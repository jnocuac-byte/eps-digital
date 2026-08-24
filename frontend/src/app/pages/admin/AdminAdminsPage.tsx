import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Plus, Trash2, Shield, X, Loader2, Crown } from 'lucide-react';
import { authApi } from '../../lib/apiClient';

interface AdminForm {
  correo: string;
  password: string;
  nombres: string;
}

const emptyForm: AdminForm = { correo: '', password: '', nombres: '' };

export default function AdminAdminsPage() {
  const qc = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<AdminForm>(emptyForm);

  const { data: admins = [], isLoading, refetch } = useQuery({
    queryKey: ['admins'],
    queryFn: async () => {
      const res = await authApi.getAdmins();
      return res.data;
    },
  });

  const crear = useMutation({
    mutationFn: (data: AdminForm) => authApi.createAdmin(data),
    onSuccess: (res) => {
      toast.success(res.data.message || 'Admin creado');
      qc.invalidateQueries({ queryKey: ['admins'] });
      setModalOpen(false);
      setForm(emptyForm);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Error al crear admin');
    },
  });

  const eliminar = useMutation({
    mutationFn: (id: string) => authApi.deleteAdmin(id),
    onSuccess: () => {
      toast.success('Admin eliminado');
      qc.invalidateQueries({ queryKey: ['admins'] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || 'Error al eliminar admin');
    },
  });

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Shield size={28} className="text-[#2B3E59]" />
          <div>
            <h1 className="text-2xl font-semibold text-[#2B3E59]">Gestión de Administradores</h1>
            <p className="text-gray-500 text-sm mt-1">{admins.length} admins registrados</p>
          </div>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="flex items-center gap-2 bg-[#2B3E59] text-white px-5 py-2.5 rounded-lg text-sm hover:opacity-90"
        >
          <Plus size={16} /> Nuevo Admin
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={32} className="animate-spin text-[#2B3E59]" />
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-left">
                <th className="px-6 py-4 text-gray-500 font-medium">Correo</th>
                <th className="px-6 py-4 text-gray-500 font-medium">Rol</th>
                <th className="px-6 py-4 text-gray-500 font-medium">Fecha de creación</th>
                <th className="px-6 py-4 text-gray-500 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {admins.map((a: any) => (
                <tr key={a.credencial_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 font-medium text-gray-800">{a.correo}</td>
                  <td className="px-6 py-4">
                    {a.es_super_admin ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-50 text-purple-700 rounded-full text-xs font-medium">
                        <Crown size={12} /> Super Admin
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                        <Shield size={12} /> Admin
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {a.creado_en ? new Date(a.creado_en).toLocaleDateString('es-CO') : '—'}
                  </td>
                  <td className="px-6 py-4">
                    {!a.es_super_admin && (
                      <button
                        onClick={() => {
                          if (confirm('¿Eliminar este admin?')) {
                            eliminar.mutate(a.credencial_id);
                          }
                        }}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-500 transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {admins.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-12 text-gray-400">
                    No hay administradores
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal crear admin */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-[#2B3E59]">Nuevo Administrador</h2>
              <button onClick={() => setModalOpen(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                crear.mutate(form);
              }}
              className="p-6 space-y-4"
            >
              <div>
                <label className="block text-sm text-gray-600 mb-1">Nombres *</label>
                <input
                  required
                  value={form.nombres}
                  onChange={(e) => setForm({ ...form, nombres: e.target.value })}
                  placeholder="Nombre completo"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Correo *</label>
                <input
                  required
                  type="email"
                  value={form.correo}
                  onChange={(e) => setForm({ ...form, correo: e.target.value })}
                  placeholder="admin@eps.com"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">Contraseña *</label>
                <input
                  required
                  type="password"
                  minLength={8}
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Min 8 caracteres, 1 mayúscula, 1 número"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="flex-1 border border-gray-200 rounded-lg py-2.5 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={crear.isPending}
                  className="flex-1 bg-[#2B3E59] text-white rounded-lg py-2.5 text-sm hover:opacity-90 disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  {crear.isPending && <Loader2 size={15} className="animate-spin" />}
                  Crear Admin
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}