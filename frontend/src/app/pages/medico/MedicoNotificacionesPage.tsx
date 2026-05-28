import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck } from 'lucide-react';
import { notificacionesApi } from '../../lib/apiClient';
import { useAuthStore } from '../../stores/authStore';
import type { Notificacion } from '../../types';

const tipoIcono: Record<string, string> = {
  cita_nueva: '📅',
  cita_cancelada: '❌',
  recordatorio: '⏰',
  sistema: '⚙️',
};

function tiempoRelativo(fecha: string): string {
  const diff = Date.now() - new Date(fecha).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'ahora';
  if (min < 60) return `hace ${min}m`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `hace ${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `hace ${days}d`;
}

export default function MedicoNotificacionesPage() {
  const qc = useQueryClient();
  const { medicoId } = useAuthStore();
  const [filtro, setFiltro] = useState<'todas' | 'no_leidas' | 'citas' | 'sistema'>('todas');

  const { data: notificaciones = [], isLoading } = useQuery<Notificacion[]>({
    queryKey: ['notificaciones', medicoId],
    queryFn: () => notificacionesApi.getByMedico(medicoId!).then((r) => r.data),
    enabled: !!medicoId,
  });

  const marcarLeida = useMutation({
    mutationFn: (id: string) => notificacionesApi.marcarLeida(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notificaciones', medicoId] }),
  });

  const marcarTodas = useMutation({
    mutationFn: () => notificacionesApi.marcarTodasLeidas(medicoId!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notificaciones', medicoId] }),
  });

  const filtradas = notificaciones.filter((n) => {
    if (filtro === 'no_leidas') return !n.leida;
    if (filtro === 'citas') return n.tipo === 'cita_nueva' || n.tipo === 'cita_cancelada' || n.tipo === 'recordatorio';
    if (filtro === 'sistema') return n.tipo === 'sistema';
    return true;
  });

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Notificaciones</h1>
          <p className="text-gray-500 text-sm mt-1">Mantente al día con tus citas y el sistema</p>
        </div>
        <button
          onClick={() => marcarTodas.mutate()}
          disabled={marcarTodas.isPending}
          className="flex items-center gap-2 text-sm text-[#2B3E59] font-medium hover:underline disabled:opacity-60"
        >
          <CheckCheck size={16} />
          Marcar todas como leídas
        </button>
      </div>

      <div className="flex gap-2 mb-6 overflow-x-auto">
        {[
          { key: 'todas', label: 'Todas' },
          { key: 'no_leidas', label: 'No leídas' },
          { key: 'citas', label: 'Citas' },
          { key: 'sistema', label: 'Sistema' },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setFiltro(f.key as typeof filtro)}
            className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              filtro === f.key
                ? 'bg-[#2B3E59] text-white'
                : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-gray-400">Cargando...</div>
      ) : filtradas.length > 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 divide-y divide-gray-50">
          {filtradas.map((n) => (
            <div
              key={n.notificacion_id}
              onClick={() => !n.leida && marcarLeida.mutate(n.notificacion_id)}
              className={`px-6 py-4 flex items-start gap-4 cursor-pointer transition-colors ${
                !n.leida ? 'bg-blue-50/50 hover:bg-blue-50' : 'hover:bg-gray-50'
              }`}
            >
              <span className="text-xl flex-shrink-0">{tipoIcono[n.tipo] || '📋'}</span>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${!n.leida ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
                  {n.titulo}
                </p>
                <p className="text-sm text-gray-500 mt-0.5">{n.descripcion}</p>
                <p className="text-xs text-gray-400 mt-1">{tiempoRelativo(n.creado_en)}</p>
              </div>
              {!n.leida && (
                <div className="w-2.5 h-2.5 bg-blue-500 rounded-full flex-shrink-0 mt-1.5" />
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <Bell size={40} className="opacity-30" />
          <p className="text-sm">Sin notificaciones</p>
        </div>
      )}
    </div>
  );
}
