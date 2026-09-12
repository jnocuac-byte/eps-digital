import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Calendar, CheckCircle, XCircle, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { authApi, citasApi } from '../../lib/apiClient';
import { parseFechaLocal, toISODateLocal } from '../../lib/fechas';
import { useAuthStore } from '../../stores/authStore';
import type { Cita } from '../../types';

const estadoColor: Record<string, string> = {
  programada: 'bg-blue-50 text-blue-700',
  cancelada: 'bg-red-50 text-red-700',
  atendida: 'bg-green-50 text-green-700',
  no_asistio: 'bg-yellow-50 text-yellow-700',
};

function SelectorFecha({ fecha, onChange }: { fecha: string; onChange: (f: string) => void }) {
  const avanzar = (dias: number) => {
    const d = parseFechaLocal(fecha);
    d.setDate(d.getDate() + dias);
    onChange(toISODateLocal(d));
  };
  const label = new Date(fecha + 'T00:00:00').toLocaleDateString('es-CO', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });
  return (
    <div className="flex items-center gap-3">
      <button onClick={() => avanzar(-1)} className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50">
        <ChevronLeft size={16} />
      </button>
      <div className="flex items-center gap-2">
        <Calendar size={16} className="text-[#2B3E59]" />
        <input
          type="date"
          value={fecha}
          onChange={(e) => onChange(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
        />
        <span className="text-sm text-gray-500 capitalize hidden sm:block">{label}</span>
      </div>
      <button onClick={() => avanzar(1)} className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50">
        <ChevronRight size={16} />
      </button>
    </div>
  );
}

export default function MedicoCitasPage() {
  const qc = useQueryClient();
  const { setMedicoId, medicoId } = useAuthStore();
  const [fecha, setFecha] = useState(toISODateLocal(new Date()));

  useEffect(() => {
    if (!medicoId) {
      authApi.getMedicoId().then((res) => {
        setMedicoId(res.data.medico_id);
      }).catch(() => {
        toast.error('No se pudo identificar tu cuenta de médico');
      });
    }
  }, [medicoId, setMedicoId]);

  const { data: citas = [], isLoading } = useQuery<Cita[]>({
    queryKey: ['citas-medico-dia', medicoId, fecha],
    queryFn: async () => {
      if (!medicoId) return [];
      const res = await citasApi.getCitasMedico(medicoId, { fecha });
      return res.data;
    },
    enabled: !!medicoId,
  } as any);

  const cambiarEstado = useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: string }) =>
      citasApi.updateEstado(id, estado),
    onSuccess: (_, vars) => {
      toast.success(
        vars.estado === 'atendida' ? 'Cita marcada como atendida' : 'Paciente marcado como no asistió',
      );
      qc.invalidateQueries({ queryKey: ['citas-medico-dia', medicoId, fecha] });
    },
    onError: () => toast.error('Error al actualizar el estado'),
  });

  const programadas = citas.filter((c) => c.estado === 'programada');
  const resto = citas.filter((c) => c.estado !== 'programada');

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Mis Citas</h1>
          <p className="text-gray-500 text-sm mt-1">Gestiona las citas del día seleccionado</p>
        </div>
        <SelectorFecha fecha={fecha} onChange={setFecha} />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-[#2B3E59]" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <span className="text-sm font-semibold text-[#2B3E59]">
                Citas programadas ({programadas.length})
              </span>
            </div>
            {programadas.length > 0 ? (
              <div className="divide-y divide-gray-50">
                {programadas.map((c) => (
                  <div key={c.cita_id} className="px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-800">
                        {c.especialidad_nombre ?? c.tipo_servicio}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Hora: {c.hora_inicio}
                        {c.sede_nombre && ` · ${c.sede_nombre}`}
                      </p>
                      {c.descripcion_sintomas && (
                        <p className="text-xs text-gray-400 mt-1 italic">"{c.descripcion_sintomas}"</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => {
                          if (confirm('¿Marcar esta cita como atendida?')) {
                            cambiarEstado.mutate({ id: c.cita_id, estado: 'atendida' });
                          }
                        }}
                        disabled={cambiarEstado.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-xs font-medium hover:bg-green-100 transition-colors disabled:opacity-60"
                      >
                        <CheckCircle size={14} /> Atendida
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('¿Marcar este paciente como no asistió?')) {
                            cambiarEstado.mutate({ id: c.cita_id, estado: 'no_asistio' });
                          }
                        }}
                        disabled={cambiarEstado.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-yellow-50 text-yellow-700 rounded-lg text-xs font-medium hover:bg-yellow-100 transition-colors disabled:opacity-60"
                      >
                        <XCircle size={14} /> No asistió
                      </button>
                      <button
                        onClick={() => {
                          if (confirm('¿Cancelar esta cita?')) {
                            cambiarEstado.mutate({ id: c.cita_id, estado: 'cancelada' });
                          }
                        }}
                        disabled={cambiarEstado.isPending}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 text-red-700 rounded-lg text-xs font-medium hover:bg-red-100 transition-colors disabled:opacity-60"
                      >
                        <XCircle size={14} /> Cancelar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm text-center py-10">No hay citas programadas para este día</p>
            )}
          </div>

          {resto.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100">
              <div className="px-6 py-4 border-b border-gray-100">
                <span className="text-sm font-semibold text-gray-600">Historial del día ({resto.length})</span>
              </div>
              <div className="divide-y divide-gray-50">
                {resto.map((c) => (
                  <div key={c.cita_id} className="px-6 py-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-700">{c.especialidad_nombre ?? c.tipo_servicio}</p>
                      <p className="text-xs text-gray-500">{c.hora_inicio}</p>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${estadoColor[c.estado]}`}>
                      {c.estado.replace('_', ' ')}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {citas.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
              <Calendar size={40} className="opacity-30" />
              <p className="text-sm">Sin citas para el {fecha}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}