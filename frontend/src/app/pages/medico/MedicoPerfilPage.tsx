import { useAuthStore } from '../../stores/authStore';
import { User, Mail, Phone, FileText } from 'lucide-react';

export default function MedicoPerfilPage() {
  const { user } = useAuthStore();

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-[#2B3E59]">Mi Perfil</h1>
        <p className="text-gray-500 text-sm mt-1">Gestiona tu información personal</p>
      </div>

      <div className="max-w-2xl">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-20 h-20 rounded-full bg-gray-100 flex items-center justify-center">
              {user?.nombres ? (
                <img
                  src={`https://ui-avatars.com/api/?name=${user.nombres}+${user.apellidos}&background=2B3E59&color=fff&size=80&bold=true`}
                  alt="Avatar"
                  className="w-20 h-20 rounded-full"
                />
              ) : (
                <User size={32} className="text-gray-400" />
              )}
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-800">
                Dr. {user?.nombres} {user?.apellidos}
              </h2>
              <p className="text-gray-500 text-sm">Médico General</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <FileText size={18} className="text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">Documento</p>
                <p className="text-sm font-medium text-gray-800">
                  {user?.tipo_documento} {user?.numero_documento}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <Mail size={18} className="text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">Correo electrónico</p>
                <p className="text-sm font-medium text-gray-800">{user?.correo || '—'}</p>
              </div>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
              <Phone size={18} className="text-gray-400" />
              <div>
                <p className="text-xs text-gray-500">Teléfono</p>
                <p className="text-sm font-medium text-gray-800">{user?.telefono || '—'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
