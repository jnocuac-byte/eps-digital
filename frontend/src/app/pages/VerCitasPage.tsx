import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { CalendarCheck, Loader2, CalendarPlus, History, MapPin, User, Clock, AlertTriangle } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { citasApi } from '../lib/apiClient';
import type { Cita } from '../types';

const statusConfig = {
  programada: { label: 'Programada', color: 'bg-blue-100 text-blue-700' },
  cancelada: { label: 'Cancelada', color: 'bg-red-100 text-red-700' },
  atendida: { label: 'Atendida', color: 'bg-green-100 text-green-700' },
  no_asistio: { label: 'No asistió', color: 'bg-orange-100 text-orange-700' },
};

export default function VerCitasPage() {
  const { userId } = useAuthStore();

  const { data: citas = [], isLoading, error } = useQuery<Cita[]>({
    queryKey: ['citas', userId],
    queryFn: () => citasApi.getByUser(userId!).then((r) => r.data),
    enabled: !!userId,
  });

  const citasActivas = citas.filter((c) => c.estado === 'programada');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-[#2B3E59]">
          <Loader2 className="animate-spin" size={24} />
          <span>Cargando citas...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-10 text-center">
        <AlertTriangle size={48} className="text-red-400 mx-auto mb-3" />
        <p className="text-gray-600 mb-4">No se pudieron cargar tus citas. Verifica tu conexión.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <CalendarCheck size={24} className="text-[#2B3E59]" />
          <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Citas Programadas</h2>
          {citasActivas.length > 0 && (
            <span className="bg-[#2B3E59] text-white text-xs px-2 py-0.5 rounded-full">
              {citasActivas.length}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          <Link
            to="/citas/historial"
            className="flex items-center gap-1.5 border border-gray-300 text-gray-600 px-4 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors"
          >
            <History size={14} /> Historial
          </Link>
          <Link
            to="/citas/agendar"
            className="flex items-center gap-1.5 bg-[#2B3E59] text-white px-4 py-2 rounded-lg text-sm hover:bg-[#1e2d40] transition-colors"
          >
            <CalendarPlus size={14} /> Nueva cita
          </Link>
        </div>
      </div>

      {citasActivas.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
          <CalendarCheck size={56} className="text-gray-300 mx-auto mb-4" />
          <h3 className="font-inter font-semibold text-gray-600 mb-2">No tienes citas programadas</h3>
          <p className="text-gray-400 text-sm mb-6">
            Agenda tu primera cita médica y te aparecerá aquí.
          </p>
          <Link
            to="/citas/agendar"
            className="inline-flex items-center gap-2 bg-[#2B3E59] text-white px-6 py-2.5 rounded-lg text-sm hover:bg-[#1e2d40] transition-colors"
          >
            <CalendarPlus size={16} /> Agendar cita
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {citasActivas.map((cita) => (
            <CitaCard key={cita.cita_id} cita={cita} />
          ))}
        </div>
      )}
    </div>
  );
}

function CitaCard({ cita }: { cita: Cita }) {
  const status = statusConfig[cita.estado] || statusConfig.programada;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 flex flex-col sm:flex-row justify-between gap-4">
      <div className="flex gap-4">
        <div className="bg-blue-50 rounded-xl p-3 flex-shrink-0 h-fit">
          <CalendarCheck size={22} className="text-[#2B3E59]" />
        </div>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h4 className="font-inter font-semibold text-[#2B3E59]">
              {cita.tipo_servicio || cita.especialidad_nombre || 'Consulta médica'}
            </h4>
            <span className={`text-xs px-2 py-0.5 rounded-full ${status.color}`}>{status.label}</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-sm text-gray-500">
            {cita.medico_nombre && (
              <span className="flex items-center gap-1">
                <User size={12} /> Dr. {cita.medico_nombre}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock size={12} />
              {new Date(cita.fecha_cita).toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })} · {cita.hora_inicio}
            </span>
            {cita.sede_nombre && (
              <span className="flex items-center gap-1">
                <MapPin size={12} /> {cita.sede_nombre}
              </span>
            )}
          </div>
          {cita.descripcion_sintomas && (
            <p className="text-xs text-gray-400 mt-2 italic">"{cita.descripcion_sintomas}"</p>
          )}
        </div>
      </div>
      <div className="flex sm:flex-col gap-2 sm:items-end justify-end flex-shrink-0">
        <Link
          to="/citas/cancelar"
          state={{ citaId: cita.cita_id }}
          className="text-sm border border-gray-300 text-gray-600 px-4 py-1.5 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Modificar
        </Link>
      </div>
    </div>
  );
}
