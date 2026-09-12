import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, ArrowLeft, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../stores/authStore';
import { catalogoApi, citasApi } from '../lib/apiClient';
import type { Servicio, Especialidad, Medico, Sede, Cita } from '../types';

const SEDE_DEFAULT = "4bf0500a-e23a-4f57-a8e8-ce4c20223695";

// Formatea una Date local a YYYY-MM-DD sin desfase de zona horaria.
const toISODate = (d: Date): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

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
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const citaAReprogramarId = searchParams.get('reprogramar');
  const esReprogramacion = !!citaAReprogramarId;

  const [servicioId, setServicioId] = useState(searchParams.get('servicio') || '');
  const [especialidadId, setEspecialidadId] = useState('');
  const [medicoId, setMedicoId] = useState('');
  const [fecha, setFecha] = useState<Date | null>(null);
  const [hora, setHora] = useState('');
  const [sintomas, setSintomas] = useState('');
  const [sedeId, setSedeId] = useState(SEDE_DEFAULT);

  // Cita original cuando se llega desde "Cancelar o Reprogramar" (?reprogramar={cita_id}).
  const { data: citaOriginal } = useQuery<Cita>({
    queryKey: ['cita-reprogramar', citaAReprogramarId],
    queryFn: () => citasApi.getById(citaAReprogramarId!).then((r) => r.data),
    enabled: esReprogramacion,
  });

  const { data: sedes = [] } = useQuery<Sede[]>({
    queryKey: ['sedes'],
    queryFn: () => catalogoApi.getSedes().then((r) => r.data),
  });

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
    queryKey: ['medicos', servicioId, especialidadId],
    queryFn: () => catalogoApi.getMedicosDisponibles(
      servicioId, 
      especialidadId || undefined
    ).then((r) => r.data),
    enabled: !!servicioId,
  });

  useEffect(() => { setEspecialidadId(''); setMedicoId(''); }, [servicioId]);
  useEffect(() => { setMedicoId(''); }, [especialidadId]);
  useEffect(() => { setHora(''); }, [medicoId, especialidadId, fecha]);

  // Franjas horarias calculadas y validadas por el backend (America/Bogota).
  const fechaISO = fecha ? toISODate(fecha) : '';
  // En reprogramacion los filtros salen de la cita original; en agendado, de los selects.
  const slotFiltros = esReprogramacion
    ? {
        medico_id: citaOriginal?.medico_id || undefined,
        especialidad_id: citaOriginal?.especialidad_id || undefined,
        servicio_id: undefined,
      }
    : {
        medico_id: medicoId || undefined,
        especialidad_id: especialidadId || undefined,
        servicio_id: servicioId || undefined,
      };
  const tieneFiltrosSlot = !!(slotFiltros.medico_id || slotFiltros.especialidad_id || slotFiltros.servicio_id);

  const { data: slots = [], isLoading: isLoadingSlots } = useQuery<
    { hora_inicio: string; hora_fin: string }[]
  >({
    queryKey: ['slots', slotFiltros.medico_id ?? '', slotFiltros.especialidad_id ?? '', slotFiltros.servicio_id ?? '', fechaISO],
    queryFn: () =>
      citasApi
        .getSlotsDisponibles({ ...slotFiltros, fecha: fechaISO })
        .then((r) => r.data),
    enabled: !!fechaISO && tieneFiltrosSlot,
    staleTime: 0,
    refetchOnMount: 'always',
  });

  const horasDisponibles = slots.map((s) => s.hora_inicio);

  const mapTipoServicio = (nombre: string): string => {
    const lower = nombre.toLowerCase();
    if (lower.includes('general')) return 'medicina_general';
    if (lower.includes('especialista') || lower.includes('cardiología') || lower.includes('pediatría')) return 'especialista';
    if (lower.includes('urgencia')) return 'urgencias';
    if (lower.includes('laboratorio')) return 'laboratorio';
    return 'especialista'; // valor por defecto
  };

  // Los slots llegan en formato HH:MM (24h); se convierten a HH:MM:00 para el backend.
  const convertToTimeFormat = (horaStr: string): string => (horaStr ? `${horaStr}:00` : '');

  const selectedEspecialidad = especialidades.find((e) => e.especialidad_id === especialidadId);
  // En reprogramacion se conserva la duracion original de la cita (independiente del catalogo).
  const calcularDuracionOriginal = (cita: Cita): number => {
    const [h1, m1] = (cita.hora_inicio || '00:00').split(':').map(Number);
    const [h2, m2] = (cita.hora_fin || '00:20').split(':').map(Number);
    return Math.max(h2 * 60 + m2 - (h1 * 60 + m1), 10);
  };
  const duracionMinutos =
    esReprogramacion && citaOriginal
      ? calcularDuracionOriginal(citaOriginal)
      : selectedEspecialidad?.duracion_cita_minutos || 20;

  const sumarMinutos = (horaStr: string, minutos: number): string => {
    const [hours, minutes] = horaStr.split(':').map(Number);
    const totalMinutos = hours * 60 + minutes + minutos;
    const newHours = Math.floor(totalMinutos / 60);
    const newMinutes = totalMinutos % 60;
    return `${newHours.toString().padStart(2, '0')}:${newMinutes.toString().padStart(2, '0')}:00`;
  };

  const mutation = useMutation({
    mutationFn: () => {
      const horaInicioPayload = convertToTimeFormat(hora);
      if (esReprogramacion && citaAReprogramarId) {
        return citasApi.reprogramar(citaAReprogramarId, {
          nueva_fecha: fecha ? toISODate(fecha) : '',
          nueva_hora_inicio: horaInicioPayload,
          nueva_hora_fin: sumarMinutos(horaInicioPayload, duracionMinutos),
        });
      }
      return citasApi.create({
        usuario_id: userId,
        medico_id: medicoId || undefined,
        especialidad_id: especialidadId || undefined,
        tipo_servicio: mapTipoServicio(selectedServicio?.nombre || ''),
        fecha_cita: fecha ? toISODate(fecha) : '',
        hora_inicio: horaInicioPayload,
        hora_fin: sumarMinutos(horaInicioPayload, duracionMinutos),
        sede_id: sedeId,
        descripcion_sintomas: sintomas || undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['citas', userId] });
      qc.invalidateQueries({ queryKey: ['citas-historial', userId] });
      qc.invalidateQueries({ queryKey: ['slots'] });
      toast.success(esReprogramacion ? '¡Cita reprogramada exitosamente!' : '¡Cita agendada exitosamente!');
      navigate('/citas/ver');
    },
    onError: () =>
      toast.error(esReprogramacion ? 'Error al reprogramar la cita. Inténtalo de nuevo.' : 'Error al agendar la cita. Inténtalo de nuevo.'),
  });

  const selectedServicio = servicios.find((s) => s.servicio_id === servicioId);
  const selectedMedico = medicos.find((m) => m.medico_id === medicoId);

  const canSubmit = esReprogramacion
    ? !!citaOriginal && !!fecha && !!hora
    : !!(servicioId && fecha && hora);

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <CalendarDays size={28} className="text-[#2B3E59]" />
        <h2 className="font-inter text-2xl font-bold text-[#2B3E59]">
          {esReprogramacion ? 'Reprogramar Cita' : 'Agendar Nueva Cita'}
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Left column */}
            <div className="space-y-4">
              {esReprogramacion ? (
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                  <p className="text-sm font-semibold text-[#2B3E59] mb-2">Cita a reprogramar</p>
                  <p className="text-sm text-gray-800">{citaOriginal?.tipo_servicio || 'Consulta médica'}</p>
                  {citaOriginal?.medico_nombre && (
                    <p className="text-xs text-gray-500 mt-0.5">Dr. {citaOriginal.medico_nombre}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    Actual:{' '}
                    {citaOriginal
                      ? `${new Date(`${citaOriginal.fecha_cita}T00:00:00`).toLocaleDateString('es-CO', {
                          weekday: 'long', day: 'numeric', month: 'long',
                        })} · ${citaOriginal.hora_inicio.slice(0, 5)}`
                      : 'cargando...'}
                  </p>
                  <p className="text-xs text-gray-400 mt-3">
                    El servicio, el médico y la sede se mantienen. Solo puedes cambiar fecha y hora.
                  </p>
                </div>
              ) : (
                <>
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
                </>
              )}
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
                  disabled={isLoadingSlots || horasDisponibles.length === 0}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59] disabled:bg-gray-100 disabled:text-gray-500"
                >
                  <option value="">
                    {isLoadingSlots ? 'Cargando horarios...' : 'Seleccionar hora...'}
                  </option>
                  {horasDisponibles.map((h) => (
                    <option key={h} value={h}>{h}</option>
                  ))}
                </select>
                {!isLoadingSlots && fechaISO && tieneFiltrosSlot && horasDisponibles.length === 0 && (
                  <p className="text-sm text-gray-500 mt-2">
                    No hay horarios disponibles para esta fecha. Prueba con otro día o médico.
                  </p>
                )}
              </div>

              {/* Sede */}
              {!esReprogramacion && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sede</label>
                  <select
                    value={sedeId}
                    onChange={(e) => setSedeId(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                  >
                    {sedes.map((s) => (
                      <option key={s.sede_id} value={s.sede_id}>{s.nombre} - {s.direccion}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Síntomas */}
          {!esReprogramacion && (
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
          )}

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
              {esReprogramacion ? 'Confirmar Reprogramación' : 'Confirmar Cita'}
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
              { label: 'Servicio', value: esReprogramacion ? citaOriginal?.tipo_servicio : selectedServicio?.nombre },
              { label: 'Especialidad', value: esReprogramacion ? undefined : selectedEspecialidad?.nombre },
              { label: 'Médico', value: !esReprogramacion && selectedMedico ? `Dr. ${selectedMedico.nombres} ${selectedMedico.apellidos}` : undefined },
              { label: 'Fecha', value: fecha?.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }) },
              { label: 'Hora', value: hora },
              { label: 'Síntomas', value: esReprogramacion ? undefined : (sintomas ? (sintomas.length > 40 ? sintomas.substring(0, 40) + '...' : sintomas) : undefined) },
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
