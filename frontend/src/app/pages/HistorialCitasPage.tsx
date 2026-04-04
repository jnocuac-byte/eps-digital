import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { History, Loader2, Filter, CalendarCheck, User, Clock } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { citasApi } from '../lib/apiClient';
import type { Cita } from '../types';

const statusConfig: Record<string, { label: string; color: string }> = {
  programada: { label: 'Programada', color: 'bg-blue-100 text-blue-700' },
  cancelada: { label: 'Cancelada', color: 'bg-red-100 text-red-700' },
  atendida: { label: 'Atendida', color: 'bg-green-100 text-green-700' },
  no_asistio: { label: 'No asistió', color: 'bg-orange-100 text-orange-700' },
};

export default function HistorialCitasPage() {
  const { userId } = useAuthStore();
  const [filterEstado, setFilterEstado] = useState('todos');
  const [filterFecha, setFilterFecha] = useState('');

  const { data: citas = [], isLoading } = useQuery<Cita[]>({
    queryKey: ['citas-historial', userId],
    queryFn: () => citasApi.getHistorial(userId!).then((r) => r.data),
    enabled: !!userId,
  });

  // Filter locally in case the API returns programadas too
  const historial = citas.filter((c) => c.estado !== 'programada');

  const filtered = historial.filter((c) => {
    if (filterEstado !== 'todos' && c.estado !== filterEstado) return false;
    if (filterFecha && c.fecha_cita) {
      const citaDate = c.fecha_cita.substring(0, 7); // YYYY-MM
      if (citaDate !== filterFecha) return false;
    }
    return true;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="animate-spin text-[#2B3E59]" size={24} />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-5">
        <History size={24} className="text-[#2B3E59]" />
        <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Historial de Citas</h2>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 mb-5">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <Filter size={14} />
            <span>Filtros:</span>
          </div>
          <select
            value={filterEstado}
            onChange={(e) => setFilterEstado(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
          >
            <option value="todos">Todos los estados</option>
            <option value="atendida">Atendida</option>
            <option value="cancelada">Cancelada</option>
            <option value="no_asistio">No asistió</option>
          </select>
          <input
            type="month"
            value={filterFecha}
            onChange={(e) => setFilterFecha(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
          />
          {(filterEstado !== 'todos' || filterFecha) && (
            <button
              onClick={() => { setFilterEstado('todos'); setFilterFecha(''); }}
              className="text-[#2B3E59] text-sm hover:underline"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-12 text-center">
          <History size={48} className="text-gray-300 mx-auto mb-3" />
          <h3 className="font-inter font-semibold text-gray-500 mb-2">No hay citas en el historial</h3>
          <p className="text-gray-400 text-sm">
            {filterEstado !== 'todos' || filterFecha
              ? 'No hay citas que coincidan con los filtros aplicados.'
              : 'Las citas pasadas aparecerán aquí.'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          {/* Table header */}
          <div className="hidden md:grid grid-cols-5 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-100 text-xs text-gray-500 font-medium uppercase tracking-wide">
            <span>Servicio</span>
            <span>Médico</span>
            <span>Fecha y Hora</span>
            <span>Estado</span>
            <span>Sede</span>
          </div>
          <div className="divide-y divide-gray-100">
            {filtered.map((cita) => {
              const status = statusConfig[cita.estado] || statusConfig.cancelada;
              return (
                <div key={cita.cita_id} className="px-5 py-4 flex flex-col md:grid md:grid-cols-5 gap-2 md:gap-4 items-start md:items-center">
                  <div>
                    <p className="font-medium text-gray-800 text-sm">
                      {cita.tipo_servicio || cita.especialidad_nombre || 'Consulta'}
                    </p>
                    {cita.especialidad_nombre && cita.tipo_servicio !== cita.especialidad_nombre && (
                      <p className="text-gray-400 text-xs">{cita.especialidad_nombre}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-sm text-gray-600">
                    {cita.medico_nombre ? (
                      <>
                        <User size={12} className="text-gray-400" />
                        <span>Dr. {cita.medico_nombre}</span>
                      </>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 text-sm text-gray-600">
                    <Clock size={12} className="text-gray-400" />
                    <span>
                      {new Date(cita.fecha_cita).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })}
                      {cita.hora_inicio && ` · ${cita.hora_inicio}`}
                    </span>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium w-fit ${status.color}`}>
                    {status.label}
                  </span>
                  <span className="text-sm text-gray-500">{cita.sede_nombre || '—'}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-4 text-right text-sm text-gray-400">
        Total: {filtered.length} cita{filtered.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}