import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Plus, Pencil, Trash2, UserCheck, UserX, X, Loader2, Search,
  Key, Clock, ChevronDown,
} from 'lucide-react';
import { catalogoApi, authApi } from '../../lib/apiClient';
import type { MedicoConEspecialidades, Especialidad, Disponibilidad, Sede } from '../../types';

interface MedicoForm {
  nombres: string;
  apellidos: string;
  numero_registro: string;
  correo_institucional: string;
  password: string;
  activo: boolean;
}

const emptyForm: MedicoForm = {
  nombres: '', apellidos: '', numero_registro: '',
  correo_institucional: '', password: '', activo: true,
};

const DIAS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

export default function AdminMedicosPage() {
  const qc = useQueryClient();
  const [busqueda, setBusqueda] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [modalDispOpen, setModalDispOpen] = useState(false);
  const [editando, setEditando] = useState<MedicoConEspecialidades | null>(null);
  const [form, setForm] = useState<MedicoForm>(emptyForm);
  const [asignandoId, setAsignandoId] = useState<string | null>(null);
  const [espSeleccionada, setEspSeleccionada] = useState('');
  const [dispMedicoId, setDispMedicoId] = useState<string | null>(null);
  const [formDisp, setFormDisp] = useState({
    dia_semana: 1, hora_inicio: '08:00', hora_fin: '12:00',
    sede_id: '', especialidad_id: '',
  });

  const { data: medicos = [], isLoading } = useQuery({
    queryKey: ['medicos-con-especialidades'],
    queryFn: async () => { const r = await catalogoApi.getMedicosConEspecialidades(); return r.data; },
  } as any);

  const { data: especialidades = [] } = useQuery({
    queryKey: ['especialidades'],
    fn: async () => { const r = await catalogoApi.getEspecialidades(); return r.data; },
  } as any);

  const { data: sedes = [] } = useQuery({
    queryKey: ['sedes'],
    fn: async () => { const r = await catalogoApi.getSedes(); return r.data; },
  } as any);

  const { data: disponibilidades = [], refetch: refDisp } = useQuery({
    queryKey: ['disponibilidades-medico', dispMedicoId],
    queryFn: async () => {
      if (!dispMedicoId) return [];
      const r = await catalogoApi.getDisponibilidadesMedico(dispMedicoId);
      return r.data;
    },
    enabled: !!dispMedicoId,
  } as any);

  const crear = useMutation({
    mutationFn: async (data: MedicoForm) => {
      const medicoRes = await catalogoApi.createMedico({
        nombres: data.nombres,
        apellidos: data.apellidos,
        numero_registro: data.numero_registro,
        correo_institucional: data.correo_institucional,
        activo: data.activo,
      });
      return medicoRes.data;
    },
    onSuccess: async (medico) => {
      try {
        await authApi.createMedicoCredencial({
          correo: form.correo_institucional,
          password: form.password,
          usuario_id: medico.usuario_id,
        });
        toast.success('Médico y credencial creados');
      } catch {
        toast.warning('Médico creado, pero falló la credencial');
      }
      qc.invalidateQueries({ queryKey: ['medicos-con-especialidades'] });
      cerrarModal();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Error al crear médico'),
  });

  const actualizar = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MedicoForm> }) =>
      catalogoApi.updateMedico(id, data as Record<string, unknown>),
    onSuccess: () => { toast.success('Médico actualizado'); qc.invalidateQueries({ queryKey: ['medicos-con-especialidades'] }); cerrarModal(); },
    onError: () => toast.error('Error al actualizar médico'),
  });

  const eliminar = useMutation({
    mutationFn: (id: string) => catalogoApi.deleteMedico(id),
    onSuccess: () => { toast.success('Médico eliminado'); qc.invalidateQueries({ queryKey: ['medicos-con-especialidades'] }); },
    onError: () => toast.error('Error al eliminar médico'),
  });

  const asignarEsp = useMutation({
    mutationFn: ({ medicoId, espId }: { medicoId: string; espId: string }) =>
      catalogoApi.asignarEspecialidad(medicoId, espId),
    onSuccess: () => { toast.success('Especialidad asignada'); qc.invalidateQueries({ queryKey: ['medicos-con-especialidades'] }); setAsignandoId(null); setEspSeleccionada(''); },
    onError: () => toast.error('Error al asignar especialidad'),
  });

  const crearDisp = useMutation({
    mutationFn: (data: any) => catalogoApi.createDisponibilidad(data),
    onSuccess: () => { toast.success('Horario creado'); refDisp(); setModalDispOpen(false); setFormDisp({ dia_semana: 1, hora_inicio: '08:00', hora_fin: '12:00', sede_id: '', especialidad_id: '' }); },
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Error al crear horario'),
  });

  const eliminarDisp = useMutation({
    mutationFn: (id: string) => catalogoApi.deleteDisponibilidad(id),
    onSuccess: () => { toast.success('Horario eliminado'); refDisp(); },
    onError: () => toast.error('Error al eliminar horario'),
  });

  const abrirCrear = () => { setEditando(null); setForm(emptyForm); setModalOpen(true); };
  const abrirEditar = (m: MedicoConEspecialidades) => {
    setEditando(m);
    setForm({ nombres: m.nombres, apellidos: m.apellidos, numero_registro: m.numero_registro, correo_institucional: m.correo_institucional, password: '', activo: m.activo });
    setModalOpen(true);
  };
  const cerrarModal = () => { setModalOpen(false); setEditando(null); setForm(emptyForm); };
  const abrirDisponibilidad = (medicoId: string) => { setDispMedicoId(medicoId); setModalDispOpen(true); };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editando) {
      const data = { ...form };
      delete (data as any).password;
      actualizar.mutate({ id: editando.medico_id, data });
    } else {
      if (!form.password) { toast.error('La contraseña es requerida'); return; }
      crear.mutate(form);
    }
  };

  const medicosFiltrados = medicos.filter(
    (m: any) =>
      `${m.nombres} ${m.apellidos}`.toLowerCase().includes(busqueda.toLowerCase()) ||
      (m.numero_registro || '').toLowerCase().includes(busqueda.toLowerCase()),
  );

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Gestión de Médicos</h1>
          <p className="text-gray-500 text-sm mt-1">{medicos.length} médicos registrados</p>
        </div>
        <button onClick={abrirCrear} className="flex items-center gap-2 bg-[#2B3E59] text-white px-5 py-2.5 rounded-lg text-sm hover:opacity-90">
          <Plus size={16} /> Nuevo Médico
        </button>
      </div>

      <div className="relative mb-6 max-w-sm">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar por nombre o registro…"
          className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30" />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20"><Loader2 size={32} className="animate-spin text-[#2B3E59]" /></div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left">
                  <th className="px-5 py-4 text-gray-500 font-medium">Médico</th>
                  <th className="px-5 py-4 text-gray-500 font-medium">Registro</th>
                  <th className="px-5 py-4 text-gray-500 font-medium">Correo</th>
                  <th className="px-5 py-4 text-gray-500 font-medium">Especialidades</th>
                  <th className="px-5 py-4 text-gray-500 font-medium">Horario</th>
                  <th className="px-5 py-4 text-gray-500 font-medium">Estado</th>
                  <th className="px-5 py-4 text-gray-500 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {medicosFiltrados.map((m: any) => (
                  <tr key={m.medico_id} className="hover:bg-gray-50">
                    <td className="px-5 py-4 font-medium text-gray-800">{m.nombres} {m.apellidos}</td>
                    <td className="px-5 py-4 text-gray-600">{m.numero_registro || '—'}</td>
                    <td className="px-5 py-4 text-gray-600">{m.correo_institucional}</td>
                    <td className="px-5 py-4">
                      <div className="flex flex-wrap gap-1">
                        {(m.especialidades || []).map((e: any) => (
                          <span key={e.especialidad_id} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs">{e.nombre}</span>
                        ))}
                        {asignandoId === m.medico_id ? (
                          <div className="flex items-center gap-1">
                            <select value={espSeleccionada} onChange={(e) => setEspSeleccionada(e.target.value)} className="text-xs border border-gray-200 rounded px-1 py-0.5">
                              <option value="">Seleccionar…</option>
                              {especialidades.map((e: Especialidad) => (
                                <option key={e.especialidad_id} value={e.especialidad_id}>{e.nombre}</option>
                              ))}
                            </select>
                            <button onClick={() => espSeleccionada && asignarEsp.mutate({ medicoId: m.medico_id, espId: espSeleccionada })}
                              className="text-xs bg-[#2B3E59] text-white px-2 py-0.5 rounded">Ok</button>
                            <button onClick={() => setAsignandoId(null)} className="text-gray-400 hover:text-gray-600"><X size={12} /></button>
                          </div>
                        ) : (
                          <button onClick={() => setAsignandoId(m.medico_id)}
                            className="px-2 py-0.5 border border-dashed border-gray-300 text-gray-400 rounded-full text-xs hover:border-[#2B3E59] hover:text-[#2B3E59]">+ Asignar</button>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <button onClick={() => abrirDisponibilidad(m.medico_id)}
                        className="flex items-center gap-1 text-xs text-[#2B3E59] hover:underline">
                        <Clock size={12} /> Ver horarios
                      </button>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${m.activo ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                        {m.activo ? <><UserCheck size={12} /> Activo</> : <><UserX size={12} /> Inactivo</>}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <button onClick={() => abrirEditar(m)} className="p-1.5 rounded-lg hover:bg-blue-50 text-blue-600" title="Editar"><Pencil size={15} /></button>
                        <button onClick={() => { if (confirm('¿Eliminar este médico?')) eliminar.mutate(m.medico_id); }}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-red-500" title="Eliminar"><Trash2 size={15} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
                {medicosFiltrados.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-12 text-gray-400">No hay médicos</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modal crear/editar médico */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-[#2B3E59]">{editando ? 'Editar Médico' : 'Nuevo Médico'}</h2>
              <button onClick={cerrarModal} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Nombres *</label>
                  <input required value={form.nombres} onChange={(e) => setForm({ ...form, nombres: e.target.value })}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30" />
                </div>
                <div>
                  <label className="block text-sm text-gray-600 mb-1">Apellidos *</label>
                  <input required value={form.apellidos} onChange={(e) => setForm({ ...form, apellidos: e.target.value })}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">N.º Registro *</label>
                <input required value={form.numero_registro} onChange={(e) => setForm({ ...form, numero_registro: e.target.value })}
                  placeholder="RM-12345" className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Correo institucional *</label>
                <input required type="email" value={form.correo_institucional}
                  onChange={(e) => setForm({ ...form, correo_institucional: e.target.value })}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30" />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">
                  {editando ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña *'}
                </label>
                <input type="password" value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder={editando ? 'Dejar vacío para no cambiar' : 'Min 8 chars, 1 mayúscula, 1 número'}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="activo" checked={form.activo}
                  onChange={(e) => setForm({ ...form, activo: e.target.checked })} className="rounded" />
                <label htmlFor="activo" className="text-sm text-gray-600">Médico activo</label>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={cerrarModal}
                  className="flex-1 border border-gray-200 rounded-lg py-2.5 text-sm text-gray-600 hover:bg-gray-50">Cancelar</button>
                <button type="submit" disabled={crear.isPending || actualizar.isPending}
                  className="flex-1 bg-[#2B3E59] text-white rounded-lg py-2.5 text-sm hover:opacity-90 disabled:opacity-60 flex items-center justify-center gap-2">
                  {crear.isPending && <Loader2 size={15} className="animate-spin" />}
                  {editando ? 'Guardar cambios' : 'Crear médico'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal disponibilidad */}
      {modalDispOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-[#2B3E59]">Horarios del Médico</h2>
              <button onClick={() => setModalDispOpen(false)} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>
            <div className="p-6 space-y-4">
              {/* Agregar horario */}
              <div className="bg-gray-50 rounded-xl p-4 space-y-3">
                <p className="text-sm font-semibold text-gray-700">Agregar horario</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Día *</label>
                    <select value={formDisp.dia_semana} onChange={(e) => setFormDisp({ ...formDisp, dia_semana: Number(e.target.value) })}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                      {DIAS.map((d, i) => <option key={i} value={i}>{d}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Sede *</label>
                    <select value={formDisp.sede_id} onChange={(e) => setFormDisp({ ...formDisp, sede_id: e.target.value })}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                      <option value="">Sede…</option>
                      {sedes.map((s: Sede) => <option key={s.sede_id} value={s.sede_id}>{s.nombre}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Especialidad *</label>
                    <select value={formDisp.especialidad_id} onChange={(e) => setFormDisp({ ...formDisp, especialidad_id: e.target.value })}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm">
                      <option value="">Especialidad…</option>
                      {especialidades.map((e: Especialidad) => <option key={e.especialidad_id} value={e.especialidad_id}>{e.nombre}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Hora inicio *</label>
                    <input type="time" value={formDisp.hora_inicio}
                      onChange={(e) => setFormDisp({ ...formDisp, hora_inicio: e.target.value })}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Hora fin *</label>
                    <input type="time" value={formDisp.hora_fin}
                      onChange={(e) => setFormDisp({ ...formDisp, hora_fin: e.target.value })}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm" />
                  </div>
                </div>
                <button onClick={() => crearDisp.mutate({ ...formDisp, medico_id: dispMedicoId })}
                  disabled={crearDisp.isPending || !formDisp.sede_id || !formDisp.especialidad_id}
                  className="w-full bg-[#2B3E59] text-white rounded-lg py-2 text-sm hover:opacity-90 disabled:opacity-60">
                  {crearDisp.isPending ? 'Guardando…' : 'Agregar horario'}
                </button>
              </div>

              {/* Lista de horarios */}
              {(disponibilidades || []).length > 0 ? (
                <div className="space-y-2">
                  <p className="text-sm font-semibold text-gray-700">Horarios configurados</p>
                  {(disponibilidades as Disponibilidad[]).map((d) => (
                    <div key={d.disponibilidad_id} className="flex items-center justify-between bg-white border border-gray-100 rounded-lg px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{DIAS[d.dia_semana]}</p>
                        <p className="text-xs text-gray-500">{d.hora_inicio} – {d.hora_fin}</p>
                      </div>
                      <button onClick={() => { if (confirm('¿Eliminar horario?')) eliminarDisp.mutate(d.disponibilidad_id); }}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-400">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400 text-center py-4">No hay horarios configurados</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}