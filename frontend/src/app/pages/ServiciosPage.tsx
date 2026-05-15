import { useState } from 'react';
import { Link } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import {
  Search, Loader2, Stethoscope, Heart, Baby, Smile,
  Brain, Eye, Bone, Syringe, Pill, Activity, User, Microscope,
  ChevronDown, CalendarPlus, X
} from 'lucide-react';
import { catalogoApi } from '../lib/apiClient';
import type { Servicio, Especialidad } from '../types';

// Fallback services if API is unavailable
const FALLBACK_SERVICES: Servicio[] = [
  { servicio_id: '1', nombre: 'Medicina General', descripcion: 'Consultas de salud integral y atención primaria', disponible: true },
  { servicio_id: '2', nombre: 'Cardiología', descripcion: 'Cuidado del corazón y sistema circulatorio', disponible: true },
  { servicio_id: '3', nombre: 'Pediatría', descripcion: 'Atención médica especializada para niños', disponible: false },
  { servicio_id: '4', nombre: 'Odontología', descripcion: 'Salud bucal y dental integral', disponible: true },
  { servicio_id: '5', nombre: 'Neurología', descripcion: 'Diagnóstico y tratamiento del sistema nervioso', disponible: true },
  { servicio_id: '6', nombre: 'Ginecología', descripcion: 'Salud femenina y atención obstétrica', disponible: true },
  { servicio_id: '7', nombre: 'Oftalmología', descripcion: 'Cuidado de la visión y salud ocular', disponible: true },
  { servicio_id: '8', nombre: 'Traumatología', descripcion: 'Lesiones y sistema musculoesquelético', disponible: false },
  { servicio_id: '9', nombre: 'Dermatología', descripcion: 'Salud de la piel, cabello y uñas', disponible: true },
  { servicio_id: '10', nombre: 'Psiquiatría', descripcion: 'Salud mental y bienestar emocional', disponible: true },
  { servicio_id: '11', nombre: 'Endocrinología', descripcion: 'Hormonas, metabolismo y diabetes', disponible: true },
  { servicio_id: '12', nombre: 'Laboratorio Clínico', descripcion: 'Exámenes y análisis clínicos', disponible: true },
];

function getServiceIcon(name: string, size = 32) {
  const n = name.toLowerCase();
  if (n.includes('general') || n.includes('medicina')) return <Stethoscope size={size} />;
  if (n.includes('cardio')) return <Heart size={size} />;
  if (n.includes('pedia')) return <Baby size={size} />;
  if (n.includes('odonto') || n.includes('dental')) return <Smile size={size} />;
  if (n.includes('neuro')) return <Brain size={size} />;
  if (n.includes('oftal') || n.includes('vision') || n.includes('ojo')) return <Eye size={size} />;
  if (n.includes('trauma') || n.includes('hueso') || n.includes('oseo')) return <Bone size={size} />;
  if (n.includes('vacu') || n.includes('inyec')) return <Syringe size={size} />;
  if (n.includes('farmac') || n.includes('medic')) return <Pill size={size} />;
  if (n.includes('labora') || n.includes('examen')) return <Microscope size={size} />;
  if (n.includes('ginec') || n.includes('obstet')) return <Activity size={size} />;
  if (n.includes('psiq') || n.includes('mental')) return <Brain size={size} />;
  if (n.includes('endoc') || n.includes('hormona')) return <Activity size={size} />;
  if (n.includes('derma') || n.includes('piel')) return <User size={size} />;
  return <User size={size} />;
}

// Modal for especialidades
function EspecialidadesModal({
  servicio,
  onClose,
}: {
  servicio: Servicio;
  onClose: () => void;
}) {
  const { data: especialidades = [], isLoading } = useQuery<Especialidad[]>({
    queryKey: ['especialidades', servicio.servicio_id],
    queryFn: () =>
      catalogoApi.getEspecialidades(servicio.servicio_id).then((r) => r.data),
    retry: 1,
  });

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b border-gray-100"
          style={{ background: 'linear-gradient(135deg, #2B3E59, #3a527a)' }}
        >
          <div className="flex items-center gap-3 text-white">
            <div className="bg-white/20 rounded-full p-2">
              {getServiceIcon(servicio.nombre, 20)}
            </div>
            <div>
              <h3 className="font-inter font-semibold">{servicio.nombre}</h3>
              <p className="text-white/70 text-xs">Especialidades disponibles</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-white/80 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="animate-spin text-[#2B3E59]" size={24} />
            </div>
          ) : especialidades.length === 0 ? (
            <div className="text-center py-10">
              <Stethoscope size={40} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">
                No hay especialidades específicas registradas para este servicio.
              </p>
              <p className="text-gray-400 text-xs mt-1">
                Puedes agendar directamente con la categoría del servicio.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {especialidades.map((esp) => (
                <div
                  key={esp.especialidad_id}
                  className="flex items-center justify-between p-3 rounded-xl border border-gray-100 hover:border-[#2B3E59]/30 hover:bg-blue-50/30 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center flex-shrink-0 text-[#2B3E59] group-hover:bg-[#2B3E59]/10">
                      {getServiceIcon(esp.nombre, 16)}
                    </div>
                    <span className="text-sm text-gray-700 font-medium">{esp.nombre}</span>
                  </div>
                  <Link
                    to={`/citas/agendar?servicio=${servicio.servicio_id}`}
                    className="text-xs text-[#2B3E59] border border-[#2B3E59]/30 px-3 py-1 rounded-full hover:bg-[#2B3E59] hover:text-white transition-colors flex items-center gap-1 flex-shrink-0"
                  >
                    <CalendarPlus size={12} /> Agendar
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-100 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border border-gray-300 text-gray-600 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors"
          >
            Cerrar
          </button>
          {servicio.activo && (
            <Link
              to={`/citas/agendar?servicio=${servicio.servicio_id}`}
              className="flex-1 bg-[#2B3E59] text-white py-2 rounded-lg text-sm font-medium hover:bg-[#1e2d40] transition-colors flex items-center justify-center gap-2"
            >
              <CalendarPlus size={14} /> Agendar cita
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

// Service Card
function ServicioCard({
  servicio,
  onVerEspecialidades,
}: {
  servicio: Servicio;
  onVerEspecialidades: (s: Servicio) => void;
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col items-center text-center hover:shadow-md hover:border-[#2B3E59]/20 transition-all group">
      <div className="bg-blue-50 group-hover:bg-[#2B3E59]/10 rounded-full p-4 mb-4 text-[#2B3E59] transition-colors">
        {getServiceIcon(servicio.nombre)}
      </div>
      <h3 className="font-inter font-semibold text-[#2B3E59] mb-2">{servicio.nombre}</h3>
      <p className="text-gray-500 text-sm leading-relaxed mb-4 flex-1">{servicio.descripcion}</p>

      <span
        className={`text-xs font-semibold px-3 py-1 rounded-full mb-4
          ${servicio.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'}`}
      >
        {servicio.activo ? '● Disponible' : '● No Disponible'}
      </span>

      {servicio.activo ? (
        <div className="flex flex-col gap-2 w-full">
          <button
            onClick={() => onVerEspecialidades(servicio)}
            className="w-full flex items-center justify-center gap-1.5 text-sm border-2 border-[#2B3E59] text-[#2B3E59] py-2 rounded-lg hover:bg-[#2B3E59] hover:text-white transition-colors"
          >
            <ChevronDown size={14} /> Ver especialidades
          </button>
          <Link
            to={`/citas/agendar?servicio=${servicio.servicio_id}`}
            className="w-full flex items-center justify-center gap-1.5 text-sm bg-[#2B3E59] text-white py-2 rounded-lg hover:bg-[#1e2d40] transition-colors"
          >
            <CalendarPlus size={14} /> Agendar
          </Link>
        </div>
      ) : (
        <div className="w-full text-center border border-gray-200 text-gray-400 text-sm py-2 rounded-lg cursor-not-allowed">
          No disponible
        </div>
      )}
    </div>
  );
}

export default function ServiciosPage() {
  const [search, setSearch] = useState('');
  const [selectedServicio, setSelectedServicio] = useState<Servicio | null>(null);
  const [filtroDisponible, setFiltroDisponible] = useState<'todos' | 'disponible' | 'no_disponible'>('todos');

  const { data: apiServicios, isLoading, error } = useQuery<Servicio[]>({
    queryKey: ['servicios'],
    queryFn: () => catalogoApi.getServicios().then((r) => r.data),
    retry: 1,
  });

  const servicios = error || !apiServicios ? FALLBACK_SERVICES : apiServicios;

  const filtered = servicios.filter((s) => {
    const matchSearch =
      s.nombre.toLowerCase().includes(search.toLowerCase()) ||
      s.descripcion.toLowerCase().includes(search.toLowerCase());
    const matchDisp =
      filtroDisponible === 'todos' ||
      (filtroDisponible === 'disponible' && s.activo) ||
      (filtroDisponible === 'no_disponible' && !s.activo);
    return matchSearch && matchDisp;
  });

  const disponiblesCount = servicios.filter((s) => s.activo).length;

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-10">
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="font-inter text-3xl md:text-4xl font-bold text-[#2B3E59] mb-3">
          Nuestros Servicios
        </h1>
        <p className="text-gray-500 max-w-xl mx-auto">
          Encuentra la especialidad médica que necesitas y agenda tu cita fácilmente.
        </p>

        {/* Stats bar */}
        <div className="flex items-center justify-center gap-6 mt-6">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-green-500 inline-block" />
            <span className="text-sm text-gray-600">{disponiblesCount} servicios disponibles</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" />
            <span className="text-sm text-gray-600">{servicios.length - disponiblesCount} temporalmente no disponibles</span>
          </div>
        </div>
      </div>

      {/* Search + Filtros */}
      <div className="max-w-3xl mx-auto mb-8 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar servicio o especialidad..."
            className="w-full bg-white border border-gray-200 rounded-2xl pl-11 pr-5 py-3.5 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X size={16} />
            </button>
          )}
        </div>
        <div className="flex gap-2">
          {(['todos', 'disponible', 'no_disponible'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFiltroDisponible(f)}
              className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors
                ${filtroDisponible === f
                  ? 'bg-[#2B3E59] text-white border-[#2B3E59]'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-[#2B3E59]/40'
                }`}
            >
              {f === 'todos' ? 'Todos' : f === 'disponible' ? 'Disponibles' : 'No disp.'}
            </button>
          ))}
        </div>
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="animate-spin text-[#2B3E59]" size={28} />
        </div>
      ) : (
        <>
          {/* Source notice */}
          {error && (
            <div className="max-w-2xl mx-auto mb-6">
              <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                <p className="text-amber-700 text-xs">
                  Mostrando servicios de referencia. La conexión con el catálogo no está disponible en este momento.
                </p>
              </div>
            </div>
          )}

          {/* Services Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {filtered.map((servicio) => (
              <ServicioCard
                key={servicio.servicio_id}
                servicio={servicio}
                onVerEspecialidades={setSelectedServicio}
              />
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="text-center py-16">
              <Search size={48} className="text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No se encontraron servicios para "{search}"</p>
              <button
                onClick={() => { setSearch(''); setFiltroDisponible('todos'); }}
                className="text-[#2B3E59] text-sm hover:underline mt-2"
              >
                Limpiar búsqueda
              </button>
            </div>
          )}

          {/* CTA Banner */}
          {filtered.length > 0 && (
            <div
              className="mt-12 rounded-2xl p-8 text-white text-center"
              style={{ background: 'linear-gradient(135deg, #2B3E59, #3a527a)' }}
            >
              <h2 className="font-inter text-xl font-bold mb-2">
                ¿No encuentras lo que buscas?
              </h2>
              <p className="text-white/80 text-sm mb-5">
                Nuestro asistente virtual puede orientarte y ayudarte a encontrar el especialista indicado.
              </p>
              <Link
                to="/asistente"
                className="inline-flex items-center gap-2 bg-white text-[#2B3E59] font-semibold px-6 py-2.5 rounded-full hover:bg-blue-50 transition-colors text-sm"
              >
                Consultar al Asistente EPSIA
              </Link>
            </div>
          )}
        </>
      )}

      {/* Especialidades Modal */}
      {selectedServicio && (
        <EspecialidadesModal
          servicio={selectedServicio}
          onClose={() => setSelectedServicio(null)}
        />
      )}
    </div>
  );
}