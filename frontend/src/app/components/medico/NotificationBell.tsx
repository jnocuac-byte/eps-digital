import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Bell } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
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

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { medicoId } = useAuthStore();

  const { data: notificaciones = [] } = useQuery<Notificacion[]>({
    queryKey: ['notificaciones', medicoId],
    queryFn: () => notificacionesApi.getByMedico(medicoId!).then((r) => r.data),
    enabled: !!medicoId,
    refetchInterval: 30000,
  });

  const noLeidas = notificaciones.filter((n) => !n.leida).length;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
      >
        <Bell size={20} className="text-gray-600" />
        {noLeidas > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center">
            {noLeidas > 9 ? '9+' : noLeidas}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-100 z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800 text-sm">Notificaciones</h3>
            {noLeidas > 0 && (
              <span className="text-xs text-[#2B3E59] font-medium">{noLeidas} nuevas</span>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notificaciones.length > 0 ? (
              notificaciones.slice(0, 5).map((n) => (
                <div
                  key={n.notificacion_id}
                  className={`px-4 py-3 hover:bg-gray-50 cursor-pointer transition-colors border-b border-gray-50 last:border-0 ${
                    !n.leida ? 'bg-blue-50/50' : ''
                  }`}
                  onClick={() => {
                    setOpen(false);
                    navigate('/medico/notificaciones');
                  }}
                >
                  <div className="flex items-start gap-3">
                    <span className="text-lg flex-shrink-0">{tipoIcono[n.tipo] || '📋'}</span>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${!n.leida ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
                        {n.titulo}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{n.descripcion}</p>
                      <p className="text-xs text-gray-400 mt-1">{tiempoRelativo(n.creado_en)}</p>
                    </div>
                    {!n.leida && (
                      <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 mt-1.5" />
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="px-4 py-8 text-center text-gray-400 text-sm">
                Sin notificaciones
              </div>
            )}
          </div>

          <div className="px-4 py-2.5 border-t border-gray-100">
            <button
              onClick={() => {
                setOpen(false);
                navigate('/medico/notificaciones');
              }}
              className="w-full text-center text-sm text-[#2B3E59] font-medium hover:underline"
            >
              Ver todas
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
