import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Calendar, Clock, CheckCircle, Loader2, AlertTriangle } from 'lucide-react';
import { authApi, citasApi } from '../../lib/apiClient';
import { toISODateLocal } from '../../lib/fechas';
import { useAuthStore } from '../../stores/authStore';
import type { Cita } from '../../types';

const PRIMARY = '#2B3E59';

const estadoColor: Record<string, string> = {
  programada: 'bg-blue-50 text-blue-700',
  cancelada: 'bg-red-50 text-red-700',
  atendida: 'bg-green-50 text-green-700',
  no_asistio: 'bg-yellow-50 text-yellow-700',
};

function MetricCard({ label, value, icon, color = PRIMARY }: {
  label: string; value: number; icon: React.ReactNode; color?: string;
}) {
  return (
    <div className="metric-card bg-white rounded-2xl shadow-sm border border-gray-100 p-5 flex items-center gap-4 transition-[box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-md">
      <div className="rounded-2xl p-3.5" style={{ backgroundColor: `${color}18` }}>
        <div style={{ color }}>{icon}</div>
      </div>
      <div>
        <p className="text-gray-500 text-sm">{label}</p>
        <p key={value} className="metric-value text-3xl font-semibold tracking-tight text-gray-800">{value}</p>
      </div>
    </div>
  );
}

export default function MedicoDashboardPage() {
  const { userId, setMedicoId, medicoId } = useAuthStore();

  const hoy = toISODateLocal(new Date());
  const en7Dias = toISODateLocal(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000));
  const inicioMes = toISODateLocal(new Date(new Date().getFullYear(), new Date().getMonth(), 1));

  useEffect(() => {
    if (userId && !medicoId) {
      authApi.getMedicoId().then((res) => {
        setMedicoId(res.data.medico_id);
      }).catch(() => {
        toast.error('No se pudo obtener tu ID de médico');
      });
    }
  }, [userId, medicoId, setMedicoId]);

  const { data: citas = [], isLoading } = useQuery<Cita[]>({
    queryKey: ['citas-medico', medicoId, 'dashboard'],
    queryFn: async () => {
      if (!medicoId) return [];
      const res = await citasApi.getCitasMedico(medicoId, {
        fecha_inicio: inicioMes,
        fecha_fin: en7Dias,
      });
      return res.data;
    },
    enabled: !!medicoId,
  } as any);

  const citasHoy = citas.filter((c) => c.fecha_cita === hoy && c.estado === 'programada');
  const proximas = citas.filter(
    (c) => c.fecha_cita > hoy && c.fecha_cita <= en7Dias && c.estado === 'programada',
  );
  const atendidasMes = citas.filter((c) => c.estado === 'atendida');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 size={36} className="animate-spin text-[#2B3E59]" />
      </div>
    );
  }

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8 lg:py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-[#2B3E59]">Mi Panel Médico</h1>
        <p className="text-gray-500 text-sm mt-2 capitalize">{new Date().toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <MetricCard label="Citas hoy" value={citasHoy.length} icon={<Calendar size={22} />} />
        <MetricCard label="Próximas 7 días" value={proximas.length} icon={<Clock size={22} />} color="#f59e0b" />
        <MetricCard label="Atendidas este mes" value={atendidasMes.length} icon={<CheckCircle size={22} />} color="#10b981" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 transition-[box-shadow,transform] duration-200 hover:shadow-md">
          <div className="flex items-center justify-between gap-3 mb-5">
            <h2 className="text-base font-semibold text-[#2B3E59]">Citas de hoy</h2>
            <span className="bg-secondary text-secondary-foreground rounded-full px-2.5 py-1 text-xs font-semibold">{citasHoy.length}</span>
          </div>
          {citasHoy.length > 0 ? (
            <ul className="space-y-3">
              {citasHoy.map((c) => (
                <li key={c.cita_id} className="flex items-center justify-between gap-4 py-3 border-b border-gray-50 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">
                      {c.especialidad_nombre ?? c.tipo_servicio}
                    </p>
                    <p className="text-xs text-gray-500">{c.hora_inicio} · {c.sede_nombre ?? 'Sin sede'}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${estadoColor[c.estado]}`}>
                    {c.estado.replace('_', ' ')}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state flex flex-col items-center justify-center py-10 px-5 text-center text-gray-500 gap-3 rounded-xl bg-gray-50/70">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-secondary text-primary">
                <Calendar size={30} strokeWidth={1.8} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-700">Tu agenda está despejada</p>
                <p className="mt-1 max-w-xs text-sm text-gray-500">No tienes citas programadas para hoy.</p>
              </div>
            </div>
          )}
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 transition-[box-shadow,transform] duration-200 hover:shadow-md">
          <div className="flex items-center justify-between gap-3 mb-5">
            <h2 className="text-base font-semibold text-[#2B3E59]">Próximas citas · 7 días</h2>
            <span className="bg-secondary text-secondary-foreground rounded-full px-2.5 py-1 text-xs font-semibold">{proximas.length}</span>
          </div>
          {proximas.length > 0 ? (
            <ul className="space-y-3">
              {proximas.slice(0, 8).map((c) => (
                <li key={c.cita_id} className="flex items-center justify-between gap-4 py-3 border-b border-gray-50 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">
                      {c.especialidad_nombre ?? c.tipo_servicio}
                    </p>
                    <p className="text-xs text-gray-500">{c.fecha_cita} · {c.hora_inicio}</p>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-xs font-semibold capitalize ${estadoColor[c.estado]}`}>
                    {c.estado.replace('_', ' ')}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="empty-state flex flex-col items-center justify-center py-10 px-5 text-center text-gray-500 gap-3 rounded-xl bg-gray-50/70">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#fff4df] text-[#9a6410]">
                <Clock size={30} strokeWidth={1.8} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-700">Todo en calma por ahora</p>
                <p className="mt-1 max-w-xs text-sm text-gray-500">No hay citas próximas en los siguientes 7 días.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}