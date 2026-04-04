import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { CalendarDays, ArrowLeft, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../stores/authStore';
import { catalogoApi, citasApi } from '../lib/apiClient';
import type { Servicio, Especialidad, Medico } from '../types';

const HORAS = [
  '07:00 AM', '07:30 AM', '08:00 AM', '08:30 AM', '09:00 AM', '09:30 AM',
  '10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM', '02:00 PM', '02:30 PM',
  '03:00 PM', '03:30 PM', '04:00 PM', '04:30 PM', '05:00 PM',
];

const DIAS = ['D', 'L', 'M', 'Mi', 'J', 'V', 'S'];
const MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

function MiniCalendar({ selected, onSelect }: { selected: Date | null; onSelect: (d: Date) => void }) {
  const today = new Date();
  const [viewDate, setViewDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));

  const daysInMonth = new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 0).getDate();
  const firstDay = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1).getDay();

  const prev = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  const next = () => setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));

  const cells: (number | null)[] = [...Array(firstDay).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];

  return (
    <div className="bg-[#2B3E59] rounded-xl p-4 text-white w-full max-w-[280px]">
      <div className="flex items-center justify-between mb-3">
        <button onClick={prev} className="p-1 hover:bg-white/20 rounded transition-colors">
          <ChevronLeft size={16} />
        </button>
        <span className="text-sm font-medium">
          {MESES[viewDate.getMonth()]} {viewDate.getFullYear()}
        </span>
        <button onClick={next} className="p-1 hover:bg-white/20 rounded transition-colors">
          <ChevronRight size={16} />
        </button>
      </div>
      <div className="grid grid-cols-7 gap-0.5 mb-1">
        {DIAS.map((d) => (
          <div key={d} className="text-center text-white/60 text-xs py-1">{d}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((day, i) => {
          if (!day) return <div key={i} />;
          const date = new Date(viewDate.getFullYear(), viewDate.getMonth(), day);
          const isPast = date < new Date(today.getFullYear(), today.getMonth(), today.getDate());
          const isSelected = selected && date.toDateString() === selected.toDateString();
          return (
            <button
              key={i}
              disabled={isPast}
              onClick={() => onSelect(date)}
              className={`text-xs py-1.5 rounded transition-colors
                ${isPast ? 'text-white/30 cursor-not-allowed' : ''}
                ${isSelected ? 'bg-white text-[#2B3E59] font-semibold' : 'hover:bg-white/20'}
              `}
            >
              {day}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function AgendarCitaPage() {
  const { userId } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [servicioId, setServicioId] = useState(searchParams.get('servicio') || '');
  const [especialidadId, setEspecialidadId] = useState('');
  const [medicoId, setMedicoId] = useState('');
  const [fecha, setFecha] = useState<Date | null>(null);
  const [hora, setHora] = useState('');
  const [sintomas, setSintomas] = useState('');

  const { data: servicios = [] } = useQuery<Servicio[]>({
    queryKey: ['servicios'],
    queryFn: () => catalogoApi.getServicios().then((r) => r.data),
  });

  const { data: especialidades = [] } = useQuery<Especialidad[]>({
    queryKey: ['especialidades', servicioId],
    queryFn: () => catalogoApi.getEspecialidades(servicioId).then((r) => r.data),
    enabled: !!servicioId,
  });

  const { data: medicos = [] } = useQuery<Medico[]>({
    queryKey: ['medicos', especialidadId],
    queryFn: () => catalogoApi.getMedicos(especialidadId).then((r) => r.data),
    enabled: !!especialidadId,
  });

  useEffect(() => { setEspecialidadId(''); setMedicoId(''); }, [servicioId]);
  useEffect(() => { setMedicoId(''); }, [especialidadId]);

  const mutation = useMutation({
    mutationFn: () =>
      citasApi.create({
        usuario_id: userId,
        medico_id: medicoId || undefined,
        especialidad_id: especialidadId || undefined,
        tipo_servicio: servicioId,
        fecha_cita: fecha?.toISOString().split('T')[0],
        hora_inicio: hora,
        descripcion_sintomas: sintomas || undefined,
      }),
    onSuccess: () => {
      toast.success('¡Cita agendada exitosamente!');
      navigate('/citas/ver');
    },
    onError: () => toast.error('Error al agendar la cita. Inténtalo de nuevo.'),
  });

  const selectedServicio = servicios.find((s) => s.servicio_id === servicioId);
  const selectedEspecialidad = especialidades.find((e) => e.especialidad_id === especialidadId);
  const selectedMedico = medicos.find((m) => m.medico_id === medicoId);

  const canSubmit = servicioId && fecha && hora;

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <CalendarDays size={28} className="text-[#2B3E59]" />
        <h2 className="font-inter text-2xl font-bold text-[#2B3E59]">Agendar Nueva Cita</h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left column */}
            <div className="space-y-4">
              {/* Tipo de Servicio */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Servicio</label>
                <select
                  value={servicioId}
                  onChange={(e) => setServicioId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                >
                  <option value="">Seleccionar servicio...</option>
                  {servicios.map((s) => (
                    <option key={s.servicio_id} value={s.servicio_id}>{s.nombre}</option>
                  ))}
                </select>
              </div>

              {/* Especialidad */}
              {especialidades.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Especialidad</label>
                  <select
                    value={especialidadId}
                    onChange={(e) => setEspecialidadId(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                  >
                    <option value="">Seleccionar especialidad...</option>
                    {especialidades.map((e) => (
                      <option key={e.especialidad_id} value={e.especialidad_id}>{e.nombre}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Médico */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Médico de preferencia</label>
                <select
                  value={medicoId}
                  onChange={(e) => setMedicoId(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                >
                  <option value="">Sin preferencia</option>
                  {medicos.map((m) => (
                    <option key={m.medico_id} value={m.medico_id}>
                      Dr. {m.nombres} {m.apellidos}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Right column - Calendar */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <span className="flex items-center gap-1.5">
                    <CalendarDays size={14} /> Fecha preferida
                  </span>
                </label>
                <MiniCalendar selected={fecha} onSelect={setFecha} />
                {fecha && (
                  <p className="text-xs text-[#2B3E59] mt-2 font-medium">
                    Seleccionado: {fecha.toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                  </p>
                )}
              </div>

              {/* Hora */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hora Preferida</label>
                <select
                  value={hora}
                  onChange={(e) => setHora(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                >
                  <option value="">Seleccionar hora...</option>
                  {HORAS.map((h) => (
                    <option key={h} value={h}>{h}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Síntomas */}
          <div className="mt-5">
            <label className="block text-sm font-medium text-gray-700 mb-1">Descripción de Síntomas</label>
            <textarea
              value={sintomas}
              onChange={(e) => setSintomas(e.target.value)}
              rows={4}
              placeholder="Describe brevemente tus síntomas para que el sistema pueda asignarte el especialista correcto..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59] resize-none"
            />
          </div>

          {/* Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 mt-6">
            <Link
              to="/"
              className="flex items-center justify-center gap-1.5 border border-gray-300 text-gray-600 px-5 py-2.5 rounded-lg text-sm hover:bg-gray-50 transition-colors"
            >
              <ArrowLeft size={14} /> Volver al inicio
            </Link>
            <button
              onClick={() => mutation.mutate()}
              disabled={!canSubmit || mutation.isPending}
              className="flex-1 bg-[#2B3E59] text-white font-semibold py-2.5 rounded-lg text-sm hover:bg-[#1e2d40] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {mutation.isPending ? <Loader2 size={16} className="animate-spin" /> : null}
              Confirmar Cita
            </button>
          </div>
        </div>

        {/* Summary Card */}
        <div className="bg-[#2B3E59] rounded-2xl p-6 text-white h-fit">
          <h3 className="font-inter font-semibold text-lg mb-5 border-b border-white/20 pb-3">
            Resumen de Cita
          </h3>
          <div className="space-y-4 text-sm">
            {[
              { label: 'Servicio', value: selectedServicio?.nombre },
              { label: 'Especialidad', value: selectedEspecialidad?.nombre },
              { label: 'Médico', value: selectedMedico ? `Dr. ${selectedMedico.nombres} ${selectedMedico.apellidos}` : undefined },
              { label: 'Fecha', value: fecha?.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }) },
              { label: 'Hora', value: hora },
              { label: 'Síntomas', value: sintomas ? (sintomas.length > 40 ? sintomas.substring(0, 40) + '...' : sintomas) : undefined },
            ].map((item) => (
              <div key={item.label} className="border-b border-white/10 pb-3">
                <p className="text-white/60 text-xs mb-0.5">{item.label}:</p>
                <p className="text-white">{item.value || '—'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}