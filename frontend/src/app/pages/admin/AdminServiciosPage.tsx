import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Plus, Pencil, Trash2, X, Loader2, ChevronDown, ChevronRight } from 'lucide-react';
import { catalogoApi } from '../../lib/apiClient';
import type { Servicio, Especialidad } from '../../types';

// ─── Formulario genérico reutilizable ────────────────────────────────────────

interface ServicioForm { nombre: string; descripcion: string; activo: boolean }
interface EspecialidadForm {
  nombre: string;
  servicio_id: string;
  duracion_cita_minutos: number;
}

const emptyServicio: ServicioForm = { nombre: '', descripcion: '', activo: true };
const emptyEsp: EspecialidadForm = { nombre: '', servicio_id: '', duracion_cita_minutos: 30 };

export default function AdminServiciosPage() {
  const qc = useQueryClient();

  // ── Servicios ──
  const [modalServicio, setModalServicio] = useState(false);
  const [editServicio, setEditServicio] = useState<Servicio | null>(null);
  const [formS, setFormS] = useState<ServicioForm>(emptyServicio);
  const [expandido, setExpandido] = useState<string | null>(null);

  // ── Especialidades ──
  const [modalEsp, setModalEsp] = useState(false);
  const [editEsp, setEditEsp] = useState<Especialidad | null>(null);
  const [formE, setFormE] = useState<EspecialidadForm>(emptyEsp);

  // Cargar servicios
  const { data: servicios = [], isLoading: loadS } = useQuery<Servicio[]>({
    queryKey: ['servicios'],
    queryFn: async () => (await catalogoApi.getServicios()).data,
    onError: () => toast.error('Error al cargar servicios'),
  } as Parameters<typeof useQuery>[0]);

  // Cargar especialidades
  const { data: especialidades = [], isLoading: loadE } = useQuery<Especialidad[]>({
    queryKey: ['especialidades'],
    queryFn: async () => (await catalogoApi.getEspecialidades()).data,
    onError: () => toast.error('Error al cargar especialidades'),
  } as Parameters<typeof useQuery>[0]);

  // CRUD Servicios
  const crearS = useMutation({
    mutationFn: (d: ServicioForm) => catalogoApi.createServicio(d as Record<string, unknown>),
    onSuccess: () => { toast.success('Servicio creado'); qc.invalidateQueries({ queryKey: ['servicios'] }); cerrarS(); },
    onError: () => toast.error('Error al crear servicio'),
  });
  const actualizarS = useMutation({
    mutationFn: ({ id, d }: { id: string; d: ServicioForm }) => catalogoApi.updateServicio(id, d as Record<string, unknown>),
    onSuccess: () => { toast.success('Servicio actualizado'); qc.invalidateQueries({ queryKey: ['servicios'] }); cerrarS(); },
    onError: () => toast.error('Error al actualizar servicio'),
  });
  const eliminarS = useMutation({
    mutationFn: (id: string) => catalogoApi.deleteServicio(id),
    onSuccess: () => { toast.success('Servicio eliminado'); qc.invalidateQueries({ queryKey: ['servicios'] }); },
    onError: () => toast.error('Error al eliminar servicio'),
  });

  // CRUD Especialidades
  const crearE = useMutation({
    mutationFn: (d: EspecialidadForm) => catalogoApi.createEspecialidad(d as Record<string, unknown>),
    onSuccess: () => { toast.success('Especialidad creada'); qc.invalidateQueries({ queryKey: ['especialidades'] }); cerrarE(); },
    onError: () => toast.error('Error al crear especialidad'),
  });
  const actualizarE = useMutation({
    mutationFn: ({ id, d }: { id: string; d: EspecialidadForm }) => catalogoApi.updateEspecialidad(id, d as Record<string, unknown>),
    onSuccess: () => { toast.success('Especialidad actualizada'); qc.invalidateQueries({ queryKey: ['especialidades'] }); cerrarE(); },
    onError: () => toast.error('Error al actualizar especialidad'),
  });
  const eliminarE = useMutation({
    mutationFn: (id: string) => catalogoApi.deleteEspecialidad(id),
    onSuccess: () => { toast.success('Especialidad eliminada'); qc.invalidateQueries({ queryKey: ['especialidades'] }); },
    onError: () => toast.error('Error al eliminar especialidad'),
  });

  // Helpers
  const cerrarS = () => { setModalServicio(false); setEditServicio(null); setFormS(emptyServicio); };
  const cerrarE = () => { setModalEsp(false); setEditEsp(null); setFormE(emptyEsp); };

  const abrirEditarS = (s: Servicio) => {
    setEditServicio(s);
    setFormS({ nombre: s.nombre, descripcion: s.descripcion, activo: s.activo ?? true });
    setModalServicio(true);
  };
  const abrirEditarE = (e: Especialidad) => {
    setEditEsp(e);
    setFormE({ nombre: e.nombre, servicio_id: e.servicio_id, duracion_cita_minutos: e.duracion_cita_minutos ?? 30 });
    setModalEsp(true);
  };

  const submitS = (ev: React.FormEvent) => {
    ev.preventDefault();
    editServicio ? actualizarS.mutate({ id: editServicio.servicio_id, d: formS }) : crearS.mutate(formS);
  };
  const submitE = (ev: React.FormEvent) => {
    ev.preventDefault();
    editEsp ? actualizarE.mutate({ id: editEsp.especialidad_id, d: formE }) : crearE.mutate(formE);
  };

  const espDeServicio = (sId: string) => especialidades.filter((e) => e.servicio_id === sId);

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-semibold text-[#2B3E59] mb-8">Servicios y Especialidades</h1>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {/* ── Panel Servicios ── */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Servicios</h2>
            <button
              onClick={() => { setEditServicio(null); setFormS(emptyServicio); setModalServicio(true); }}
              className="flex items-center gap-1.5 bg-[#2B3E59] text-white px-4 py-2 rounded-lg text-sm hover:opacity-90"
            >
              <Plus size={15} /> Nuevo servicio
            </button>
          </div>

          {loadS ? (
            <div className="flex justify-center py-10"><Loader2 size={28} className="animate-spin text-[#2B3E59]" /></div>
          ) : (
            <div className="space-y-2">
              {servicios.map((s) => (
                <div key={s.servicio_id} className="bg-white rounded-xl shadow-sm border border-gray-100">
                  <div className="flex items-center justify-between px-4 py-3">
                    <button
                      onClick={() => setExpandido(expandido === s.servicio_id ? null : s.servicio_id)}
                      className="flex items-center gap-2 text-sm font-medium text-gray-800 flex-1 text-left"
                    >
                      {expandido === s.servicio_id ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      {s.nombre}
                      <span className="ml-2 text-xs text-gray-400">
                        ({espDeServicio(s.servicio_id).length} especialidades)
                      </span>
                    </button>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${s.activo ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {s.activo ? 'Activo' : 'Inactivo'}
                      </span>
                      <button onClick={() => abrirEditarS(s)} className="p-1.5 hover:bg-blue-50 rounded-lg text-blue-600">
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => confirm('¿Eliminar servicio?') && eliminarS.mutate(s.servicio_id)}
                        className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                  {expandido === s.servicio_id && (
                    <div className="px-4 pb-3 border-t border-gray-50 pt-2">
                      <p className="text-xs text-gray-500 mb-2">{s.descripcion}</p>
                      <p className="text-xs text-gray-400">Especialidades asignadas:</p>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {espDeServicio(s.servicio_id).map((e) => (
                          <span key={e.especialidad_id} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs">
                            {e.nombre} · {e.duracion_cita_minutos}min
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {servicios.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-8">No hay servicios registrados</p>
              )}
            </div>
          )}
        </div>

        {/* ── Panel Especialidades ── */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">Especialidades</h2>
            <button
              onClick={() => { setEditEsp(null); setFormE(emptyEsp); setModalEsp(true); }}
              className="flex items-center gap-1.5 bg-[#2B3E59] text-white px-4 py-2 rounded-lg text-sm hover:opacity-90"
            >
              <Plus size={15} /> Nueva especialidad
            </button>
          </div>

          {loadE ? (
            <div className="flex justify-center py-10"><Loader2 size={28} className="animate-spin text-[#2B3E59]" /></div>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-4 py-3 text-gray-500 font-medium">Nombre</th>
                    <th className="px-4 py-3 text-gray-500 font-medium">Servicio</th>
                    <th className="px-4 py-3 text-gray-500 font-medium">Duración</th>
                    <th className="px-4 py-3 text-gray-500 font-medium">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {especialidades.map((e) => (
                    <tr key={e.especialidad_id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-800">{e.nombre}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {servicios.find((s) => s.servicio_id === e.servicio_id)?.nombre ?? '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{e.duracion_cita_minutos ?? '—'} min</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button onClick={() => abrirEditarE(e)} className="p-1.5 hover:bg-blue-50 rounded-lg text-blue-600">
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => confirm('¿Eliminar especialidad?') && eliminarE.mutate(e.especialidad_id)}
                            className="p-1.5 hover:bg-red-50 rounded-lg text-red-500"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {especialidades.length === 0 && (
                    <tr><td colSpan={4} className="text-center py-10 text-gray-400">Sin especialidades</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal Servicio */}
      {modalServicio && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-[#2B3E59]">
                {editServicio ? 'Editar Servicio' : 'Nuevo Servicio'}
              </h3>
              <button onClick={cerrarS}><X size={20} className="text-gray-400" /></button>
            </div>
            <form onSubmit={submitS} className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nombre *</label>
                <input
                  required
                  value={formS.nombre}
                  onChange={(e) => setFormS({ ...formS, nombre: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Descripción</label>
                <textarea
                  rows={3}
                  value={formS.descripcion}
                  onChange={(e) => setFormS({ ...formS, descripcion: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 resize-none"
                />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="actS" checked={formS.activo} onChange={(e) => setFormS({ ...formS, activo: e.target.checked })} />
                <label htmlFor="actS" className="text-sm text-gray-600">Activo</label>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={cerrarS} className="flex-1 border border-gray-200 rounded-lg py-2.5 text-sm text-gray-600 hover:bg-gray-50">Cancelar</button>
                <button
                  type="submit"
                  disabled={crearS.isPending || actualizarS.isPending}
                  className="flex-1 bg-[#2B3E59] text-white rounded-lg py-2.5 text-sm hover:opacity-90 disabled:opacity-60"
                >
                  {editServicio ? 'Guardar' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Especialidad */}
      {modalEsp && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h3 className="text-lg font-semibold text-[#2B3E59]">
                {editEsp ? 'Editar Especialidad' : 'Nueva Especialidad'}
              </h3>
              <button onClick={cerrarE}><X size={20} className="text-gray-400" /></button>
            </div>
            <form onSubmit={submitE} className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nombre *</label>
                <input
                  required
                  value={formE.nombre}
                  onChange={(e) => setFormE({ ...formE, nombre: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Servicio *</label>
                <select
                  required
                  value={formE.servicio_id}
                  onChange={(e) => setFormE({ ...formE, servicio_id: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                >
                  <option value="">Seleccionar servicio…</option>
                  {servicios.map((s) => (
                    <option key={s.servicio_id} value={s.servicio_id}>{s.nombre}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Duración (minutos) *</label>
                <input
                  required
                  type="number"
                  min={5}
                  max={240}
                  value={formE.duracion_cita_minutos}
                  onChange={(e) => setFormE({ ...formE, duracion_cita_minutos: Number(e.target.value) })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={cerrarE} className="flex-1 border border-gray-200 rounded-lg py-2.5 text-sm text-gray-600 hover:bg-gray-50">Cancelar</button>
                <button
                  type="submit"
                  disabled={crearE.isPending || actualizarE.isPending}
                  className="flex-1 bg-[#2B3E59] text-white rounded-lg py-2.5 text-sm hover:opacity-90 disabled:opacity-60"
                >
                  {editEsp ? 'Guardar' : 'Crear'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
