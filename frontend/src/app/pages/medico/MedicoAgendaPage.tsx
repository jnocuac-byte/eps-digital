import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Calendar, Clock, User } from 'lucide-react';
import { authApi, citasApi } from '../../lib/apiClient';
import { parseFechaLocal, toISODateLocal } from '../../lib/fechas';
import { useAuthStore } from '../../stores/authStore';
import type { Cita } from '../../types';

const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const estadoColor: Record<string, string> = {
  programada: 'bg-blue-50 text-blue-700',
  cancelada: 'bg-red-50 text-red-700',
  atendida: 'bg-green-50 text-green-700',
  no_asistio: 'bg-yellow-50 text-yellow-700',
};

export default function MedicoAgendaPage() {
  const { medicoId, setMedicoId } = useAuthStore();
  const [mesActual, setMesActual] = useState(new Date());
  const [diaSeleccionado, setDiaSeleccionado] = useState<Date | null>(null);

  useEffect(() => {
    if (!medicoId) {
      authApi.getMedicoId().then((res) => {
        setMedicoId(res.data.medico_id);
      }).catch(() => {});
    }
  }, [medicoId, setMedicoId]);

  const year = mesActual.getFullYear();
  const month = mesActual.getMonth();
  const primerDia = new Date(year, month, 1).getDay();
  const diasEnMes = new Date(year, month + 1, 0).getDate();
  const offset = (primerDia + 6) % 7;

  const fechaInicio = toISODateLocal(new Date(year, month, 1));
  const fechaFin = toISODateLocal(new Date(year, month + 1, 0));

  const { data: citasMes = [] } = useQuery<Cita[]>({
    queryKey: ['citas-medico-agenda', medicoId, fechaInicio, fechaFin],
    queryFn: async () => {
      if (!medicoId) return [];
      const res = await citasApi.getCitasMedico(medicoId, { fecha_inicio: fechaInicio, fecha_fin: fechaFin });
      return res.data;
    },
    enabled: !!medicoId,
  } as any);

  const citasPorDia = useMemo(() => {
    const map: Record<number, Cita[]> = {};
    for (const c of citasMes) {
      const d = parseFechaLocal(c.fecha_cita).getDate();
      if (!map[d]) map[d] = [];
      map[d].push(c);
    }
    return map;
  }, [citasMes]);

  const dias: (number | null)[] = [];
  for (let i = 0; i < offset; i++) dias.push(null);
  for (let i = 1; i <= diasEnMes; i++) dias.push(i);

  const cambiarMes = (delta: number) => {
    const d = new Date(mesActual);
    d.setMonth(d.getMonth() + delta);
    setMesActual(d);
    setDiaSeleccionado(null);
  };

  const hoy = new Date();
  const esHoy = (dia: number) =>
    dia === hoy.getDate() && month === hoy.getMonth() && year === hoy.getFullYear();

  const seleccionado = (dia: number) =>
    diaSeleccionado?.getDate() === dia &&
    diaSeleccionado?.getMonth() === month &&
    diaSeleccionado?.getFullYear() === year;

  const citasDelDia = diaSeleccionado
    ? citasPorDia[diaSeleccionado.getDate()] ?? []
    : [];

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Mi Agenda</h1>
          <p className="text-gray-500 text-sm mt-1">Gestiona tu disponibilidad y horarios</p>
        </div>
        <button className="bg-[#2B3E59] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1e2d40] transition-colors">
          Configurar disponibilidad
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => cambiarMes(-1)} className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50">
            <ChevronLeft size={18} />
          </button>
          <h2 className="text-lg font-semibold text-gray-800">
            {MESES[month]} {year}
          </h2>
          <button onClick={() => cambiarMes(1)} className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50">
            <ChevronRight size={18} />
          </button>
        </div>

        <div className="grid grid-cols-7 gap-1">
          {DIAS.map((d) => (
            <div key={d} className="text-center text-xs font-medium text-gray-500 py-2">
              {d}
            </div>
          ))}
          {dias.map((dia, i) => {
            const tieneCitas = dia !== null && (citasPorDia[dia]?.length ?? 0) > 0;
            return (
              <div
                key={i}
                onClick={() => dia && setDiaSeleccionado(new Date(year, month, dia))}
                className={`aspect-square flex flex-col items-center justify-center rounded-lg text-sm cursor-pointer transition-colors ${
                  dia === null
                    ? ''
                    : esHoy(dia)
                    ? 'bg-[#2B3E59] text-white font-semibold'
                    : seleccionado(dia)
                    ? 'bg-blue-100 text-[#2B3E59] font-semibold'
                    : 'hover:bg-gray-100 text-gray-700'
                }`}
              >
                {dia}
                {tieneCitas && dia !== null && (
                  <span className={`w-1.5 h-1.5 rounded-full mt-0.5 ${
                    esHoy(dia) ? 'bg-white' : 'bg-blue-500'
                  }`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {diaSeleccionado && (
        <div className="mt-6 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={18} className="text-[#2B3E59]" />
            <h3 className="font-semibold text-gray-800">
              {diaSeleccionado.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
            </h3>
          </div>
          {citasDelDia.length > 0 ? (
            <div className="divide-y divide-gray-50">
              {citasDelDia.map((c) => (
                <div key={c.cita_id} className="py-3 flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    <Clock size={14} className="text-[#2B3E59]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800">
                        {c.hora_inicio} – {c.hora_fin}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${estadoColor[c.estado] ?? 'bg-gray-50 text-gray-600'}`}>
                        {c.estado.replace('_', ' ')}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">
                      {c.especialidad_nombre ?? c.tipo_servicio}
                    </p>
                    {c.descripcion_sintomas && (
                      <p className="text-xs text-gray-400 mt-1 italic">"{c.descripcion_sintomas}"</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">Sin citas programadas para este día</p>
          )}
        </div>
      )}
    </div>
  );
}
