import { useState } from 'react';
import { Link } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { RotateCcw, AlertTriangle, Loader2, CheckCircle2, X } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../stores/authStore';
import { citasApi } from '../lib/apiClient';
import type { Cita } from '../types';

export default function CancelarCitaPage() {
  const { userId } = useAuthStore();
  const qc = useQueryClient();
  const [selectedCita, setSelectedCita] = useState<Cita | null>(null);
  const [motivo, setMotivo] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);

  const { data: citas = [], isLoading } = useQuery<Cita[]>({
    queryKey: ['citas', userId],
    queryFn: () => citasApi.getByUser(userId!).then((r) => r.data),
    enabled: !!userId,
  });

  const citasActivas = citas.filter((c) => c.estado === 'programada');

  const cancelMutation = useMutation({
    mutationFn: () => citasApi.cancel(selectedCita!.cita_id, motivo || 'Sin motivo especificado'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['citas', userId] });
      qc.invalidateQueries({ queryKey: ['citas-historial', userId] });
      toast.success('Cita cancelada exitosamente');
      setConfirmOpen(false);
      setSelectedCita(null);
      setMotivo('');
    },
    onError: () => toast.error('Error al cancelar la cita'),
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
        <RotateCcw size={24} className="text-[#2B3E59]" />
        <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Cancelar o Reprogramar</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Citas List */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          <h3 className="font-medium text-gray-700 mb-4">Selecciona una cita</h3>
          {citasActivas.length === 0 ? (
            <div className="text-center py-10">
              <CheckCircle2 size={40} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No tienes citas programadas.</p>
              <Link to="/citas/agendar" className="text-[#2B3E59] text-sm hover:underline mt-2 inline-block">
                Agendar nueva cita →
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {citasActivas.map((cita) => (
                <button
                  key={cita.cita_id}
                  onClick={() => setSelectedCita(cita)}
                  className={`w-full text-left p-4 rounded-xl border-2 transition-colors
                    ${selectedCita?.cita_id === cita.cita_id
                      ? 'border-[#2B3E59] bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'}`}
                >
                  <p className="font-medium text-gray-800 text-sm">
                    {cita.tipo_servicio || cita.especialidad_nombre || 'Consulta médica'}
                  </p>
                  {cita.medico_nombre && (
                    <p className="text-gray-500 text-xs mt-0.5">Dr. {cita.medico_nombre}</p>
                  )}
                  <p className="text-gray-500 text-xs mt-1">
                    {new Date(cita.fecha_cita).toLocaleDateString('es-CO', {
                      weekday: 'long', day: 'numeric', month: 'long'
                    })} · {cita.hora_inicio}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Action Panel */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-5">
          {!selectedCita ? (
            <div className="text-center py-10 text-gray-400">
              <RotateCcw size={40} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">Selecciona una cita para ver las opciones</p>
            </div>
          ) : (
            <div>
              <h3 className="font-medium text-gray-700 mb-4">Cita seleccionada</h3>
              <div className="bg-blue-50 rounded-xl p-4 mb-5">
                <p className="font-semibold text-[#2B3E59]">
                  {selectedCita.tipo_servicio || selectedCita.especialidad_nombre}
                </p>
                {selectedCita.medico_nombre && (
                  <p className="text-gray-600 text-sm">Dr. {selectedCita.medico_nombre}</p>
                )}
                <p className="text-gray-500 text-sm">
                  {new Date(selectedCita.fecha_cita).toLocaleDateString('es-CO', {
                    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
                  })} · {selectedCita.hora_inicio}
                </p>
              </div>

              <div className="mb-5">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Motivo de cancelación (opcional)
                </label>
                <select
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59] mb-2"
                >
                  <option value="">Seleccionar motivo...</option>
                  <option value="No puedo asistir">No puedo asistir</option>
                  <option value="Mejoré de salud">Mejoré de salud</option>
                  <option value="Conflicto de horario">Conflicto de horario</option>
                  <option value="Cambio de médico">Cambio de médico</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>

              <div className="flex flex-col gap-3">
                <Link
                  to="/citas/agendar"
                  className="flex items-center justify-center gap-2 border-2 border-[#2B3E59] text-[#2B3E59] py-2.5 rounded-lg text-sm font-medium hover:bg-blue-50 transition-colors"
                >
                  Reprogramar cita
                </Link>
                <button
                  onClick={() => setConfirmOpen(true)}
                  className="flex items-center justify-center gap-2 bg-red-500 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-red-600 transition-colors"
                >
                  <X size={16} /> Cancelar esta cita
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmOpen && selectedCita && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm">
            <div className="flex justify-center mb-4">
              <div className="bg-red-100 rounded-full p-4">
                <AlertTriangle size={32} className="text-red-500" />
              </div>
            </div>
            <h3 className="font-inter font-semibold text-center text-gray-800 mb-2">
              ¿Confirmar cancelación?
            </h3>
            <p className="text-gray-500 text-sm text-center mb-5">
              Esta acción no se puede deshacer. La cita del{' '}
              <strong>{new Date(selectedCita.fecha_cita).toLocaleDateString('es-CO', { day: 'numeric', month: 'long' })}</strong>{' '}
              será cancelada.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmOpen(false)}
                className="flex-1 border border-gray-300 text-gray-600 py-2.5 rounded-lg text-sm hover:bg-gray-50"
              >
                No, mantener
              </button>
              <button
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
                className="flex-1 bg-red-500 text-white py-2.5 rounded-lg text-sm hover:bg-red-600 disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {cancelMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
                Sí, cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
