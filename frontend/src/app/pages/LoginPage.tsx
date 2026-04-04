import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, HeartPulse, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '../stores/authStore';
import { authApi, userApi } from '../lib/apiClient';

interface LoginForm {
  tipo_documento: string;
  numero_documento: string;
  password: string;
}

const TIPO_DOC_OPTIONS = [
  { value: 'CC', label: 'Cédula de Ciudadanía (CC)' },
  { value: 'CE', label: 'Cédula de Extranjería (CE)' },
  { value: 'PA', label: 'Pasaporte (PA)' },
  { value: 'TI', label: 'Tarjeta de Identidad (TI)' },
];

export default function LoginPage() {
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const { login, setUser } = useAuthStore();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ defaultValues: { tipo_documento: 'CC' } });

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    setApiError('');
    try {
      const res = await authApi.login(data);
      const { access_token, refresh_token, usuario_id } = res.data;
      login(access_token, refresh_token, usuario_id);

      // Load user profile
      try {
        const userRes = await userApi.getById(usuario_id);
        setUser(userRes.data);
      } catch {
        // Non-critical error
      }

      toast.success('¡Bienvenido!');
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      const msg =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        'Credenciales incorrectas. Verifica tu documento y contraseña.';
      setApiError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex items-center justify-center px-4 py-12">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="bg-[#2B3E59] rounded-full p-3 mb-3">
            <HeartPulse size={28} color="white" />
          </div>
          <h1 className="font-inter text-2xl font-bold text-[#2B3E59]">EPS Digital</h1>
          <p className="text-gray-500 text-sm mt-1">Inicia sesión en tu cuenta</p>
        </div>

        {apiError && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-red-600 text-sm">{apiError}</p>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Tipo de documento */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de documento
            </label>
            <select
              {...register('tipo_documento', { required: 'Selecciona el tipo de documento' })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
            >
              {TIPO_DOC_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {errors.tipo_documento && (
              <p className="text-red-500 text-xs mt-1">{errors.tipo_documento.message}</p>
            )}
          </div>

          {/* Número de documento */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Número de documento
            </label>
            <input
              {...register('numero_documento', {
                required: 'Ingresa tu número de documento',
                minLength: { value: 5, message: 'Mínimo 5 caracteres' },
              })}
              type="text"
              placeholder="Ej: 1234567890"
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
            />
            {errors.numero_documento && (
              <p className="text-red-500 text-xs mt-1">{errors.numero_documento.message}</p>
            )}
          </div>

          {/* Contraseña */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
            <div className="relative">
              <input
                {...register('password', {
                  required: 'Ingresa tu contraseña',
                  minLength: { value: 6, message: 'Mínimo 6 caracteres' },
                })}
                type={showPass ? 'text' : 'password'}
                placeholder="••••••••"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59] pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && (
              <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
            )}
          </div>

          <div className="text-right">
            <button type="button" className="text-[#2B3E59] text-sm hover:underline">
              ¿Olvidaste tu contraseña?
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-[#2B3E59] text-white font-semibold py-3 rounded-lg hover:bg-[#1e2d40] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Ingresando...
              </span>
            ) : (
              'Ingresar'
            )}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          ¿No tienes cuenta?{' '}
          <Link to="/register" className="text-[#2B3E59] font-medium hover:underline">
            Crear cuenta
          </Link>
        </p>
      </div>
    </div>
  );
}
