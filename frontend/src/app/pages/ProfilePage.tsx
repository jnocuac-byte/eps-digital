import { useState } from 'react';
import { Link } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { User, Activity, Shield, Edit3, ArrowLeft, Save, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../stores/authStore';
import { userApi } from '../lib/apiClient';
import type { UserCompleto } from '../types';

export default function ProfilePage() {
  const { userId, setUser } = useAuthStore();
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState<Record<string, string>>({});

  const { data, isLoading, error } = useQuery<UserCompleto>({
    queryKey: ['user-completo', userId],
    queryFn: () => userApi.getCompleto(userId!).then((r) => r.data),
    enabled: !!userId,
  });

  const mutation = useMutation({
    mutationFn: (updates: Record<string, string>) => userApi.update(userId!, updates),
    onSuccess: (res) => {
      setUser(res.data);
      qc.invalidateQueries({ queryKey: ['user-completo', userId] });
      toast.success('Perfil actualizado correctamente');
      setEditing(false);
    },
    onError: () => toast.error('Error al actualizar el perfil'),
  });

  const startEdit = () => {
    if (!data) return;
    setEditData({
      telefono: data.user.telefono || '',
      correo: data.user.correo || '',
      nombres: data.user.nombres || '',
      apellidos: data.user.apellidos || '',
    });
    setEditing(true);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex items-center gap-3 text-[#2B3E59]">
          <Loader2 className="animate-spin" size={24} />
          <span>Cargando perfil...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-[1440px] mx-auto px-6 py-10 text-center">
        <p className="text-red-500 mb-4">No se pudo cargar el perfil. Verifica tu conexión.</p>
        <Link to="/" className="text-[#2B3E59] hover:underline">← Volver al inicio</Link>
      </div>
    );
  }

  const { user, informacion_medica, afiliacion } = data;

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <Link to="/" className="inline-flex items-center gap-1.5 text-[#2B3E59] hover:underline text-sm mb-6">
        <ArrowLeft size={16} /> Volver al inicio
      </Link>

      {/* Profile Header */}
      <div className="rounded-2xl p-6 md:p-8 mb-6 relative border-2 border-purple-400"
        style={{ background: 'linear-gradient(135deg, #2B3E59, #3a527a)' }}
      >
        <button
          onClick={startEdit}
          className="absolute top-4 right-4 bg-white text-[#2B3E59] font-medium px-4 py-1.5 rounded-full text-sm hover:bg-blue-50 transition-colors flex items-center gap-1.5"
        >
          <Edit3 size={14} /> Editar
        </button>

        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
          <div className="bg-white/20 rounded-full p-5 flex-shrink-0">
            <User size={48} className="text-white" />
          </div>
          <div className="text-center sm:text-left">
            <h1 className="font-inter text-2xl md:text-3xl font-bold text-white">
              {user.nombres} {user.apellidos}
            </h1>
            <p className="text-white/70 mt-1 text-sm">
              Número de afiliado: {user.usuario_id?.substring(0, 12)}...
            </p>
            <div className="mt-3">
              <span className="bg-white text-[#2B3E59] font-semibold px-4 py-1.5 rounded-full text-sm">
                Afiliación: {afiliacion?.tipo_afiliacion || 'Premium'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Personal Info */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <User size={18} className="text-[#2B3E59]" />
            <h3 className="font-inter font-semibold text-[#2B3E59]">Información Personal</h3>
          </div>
          <div className="space-y-3 text-sm">
            {[
              { label: 'Documento', value: `${user.tipo_documento} ${user.numero_documento}` },
              { label: 'Fecha de Nacimiento', value: user.fecha_nacimiento ? new Date(user.fecha_nacimiento).toLocaleDateString('es-CO') : '—' },
              { label: 'Teléfono', value: user.telefono || '—' },
              { label: 'Email', value: user.correo || '—' },
            ].map((item) => (
              <div key={item.label} className="border-b border-gray-100 pb-3">
                <p className="text-gray-400 text-xs mb-0.5">{item.label}</p>
                <p className="text-gray-700">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Medical Info */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={18} className="text-[#2B3E59]" />
            <h3 className="font-inter font-semibold text-[#2B3E59]">Información Médica</h3>
          </div>
          <div className="space-y-3 text-sm">
            {[
              { label: 'Tipo de Sangre', value: informacion_medica?.tipo_sangre || '—' },
              { label: 'Alergias', value: informacion_medica?.alergias || 'Ninguna registrada' },
              { label: 'Enfermedades Crónicas', value: informacion_medica?.enfermedades_cronicas || 'Ninguna registrada' },
              { label: 'Médico Asignado', value: informacion_medica?.medico_asignado || '—' },
            ].map((item) => (
              <div key={item.label} className="border-b border-gray-100 pb-3">
                <p className="text-gray-400 text-xs mb-0.5">{item.label}</p>
                <p className="text-gray-700">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* EPS Info */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={18} className="text-[#2B3E59]" />
            <h3 className="font-inter font-semibold text-[#2B3E59]">Mi EPS</h3>
          </div>
          <div className="space-y-3 text-sm">
            {[
              { label: 'Número de Póliza', value: afiliacion?.numero_poliza || '—' },
              { label: 'Fecha de Afiliación', value: afiliacion?.fecha_afiliacion ? new Date(afiliacion.fecha_afiliacion).toLocaleDateString('es-CO') : '—' },
              { label: 'Estado', value: afiliacion?.estado || 'Activo' },
              { label: 'Tipo de Afiliación', value: afiliacion?.tipo_afiliacion || 'Premium' },
            ].map((item) => (
              <div key={item.label} className="border-b border-gray-100 pb-3">
                <p className="text-gray-400 text-xs mb-0.5">{item.label}</p>
                <p className={`font-medium ${item.label === 'Estado' ? 'text-green-600' : 'text-gray-700'}`}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Edit Modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-inter font-semibold text-[#2B3E59] text-lg">Editar perfil</h3>
              <button onClick={() => setEditing(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="space-y-4">
              {[
                { key: 'nombres', label: 'Nombres' },
                { key: 'apellidos', label: 'Apellidos' },
                { key: 'telefono', label: 'Teléfono' },
                { key: 'correo', label: 'Correo electrónico' },
              ].map((f) => (
                <div key={f.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{f.label}</label>
                  <input
                    type={f.key === 'correo' ? 'email' : 'text'}
                    value={editData[f.key] || ''}
                    onChange={(e) => setEditData((prev) => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setEditing(false)}
                className="flex-1 border border-gray-300 text-gray-600 py-2.5 rounded-lg text-sm hover:bg-gray-50 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => mutation.mutate(editData)}
                disabled={mutation.isPending}
                className="flex-1 bg-[#2B3E59] text-white py-2.5 rounded-lg text-sm hover:bg-[#1e2d40] transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {mutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
