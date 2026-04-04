import { useState } from 'react';
import { Link, useNavigate } from 'react-router';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, HeartPulse, AlertCircle, CheckCircle2, ChevronLeft } from 'lucide-react';
import { toast } from 'sonner';
import { authApi, userApi } from '../lib/apiClient';

interface Step1Form {
  tipo_documento: string;
  numero_documento: string;
  nombres: string;
  apellidos: string;
  fecha_nacimiento: string;
  acepta_terminos: boolean;
}

interface Step2Form {
  telefono: string;
  correo: string;
  password: string;
  confirm_password: string;
}

const TIPO_DOC_OPTIONS = [
  { value: 'CC', label: 'Cédula de Ciudadanía (CC)' },
  { value: 'CE', label: 'Cédula de Extranjería (CE)' },
  { value: 'PA', label: 'Pasaporte (PA)' },
  { value: 'TI', label: 'Tarjeta de Identidad (TI)' },
];

export default function RegisterPage() {
  const [step, setStep] = useState(1);
  const [step1Data, setStep1Data] = useState<Step1Form | null>(null);
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');
  const navigate = useNavigate();

  const form1 = useForm<Step1Form>({ defaultValues: { tipo_documento: 'CC', acepta_terminos: false } });
  const form2 = useForm<Step2Form>();

  const onStep1 = (data: Step1Form) => {
    if (!data.acepta_terminos) {
      form1.setError('acepta_terminos', { message: 'Debes aceptar los términos y condiciones' });
      return;
    }
    setStep1Data(data);
    setStep(2);
  };

  const onStep2 = async (data: Step2Form) => {
    if (!step1Data) return;
    if (data.password !== data.confirm_password) {
      form2.setError('confirm_password', { message: 'Las contraseñas no coinciden' });
      return;
    }

    setLoading(true);
    setApiError('');

    try {
      const registerPayload = {
        ...step1Data,
        ...data,
        acepta_terminos: step1Data.acepta_terminos,
      };

      const res = await authApi.register(registerPayload);
      const { usuario_id } = res.data;

      // Create user profile
      await userApi.create({
        usuario_id,
        nombres: step1Data.nombres,
        apellidos: step1Data.apellidos,
        tipo_documento: step1Data.tipo_documento,
        numero_documento: step1Data.numero_documento,
        fecha_nacimiento: step1Data.fecha_nacimiento,
        correo: data.correo,
        telefono: data.telefono,
      });

      toast.success('¡Registro exitoso! Por favor inicia sesión.');
      navigate('/login');
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string; message?: string } } };
      const msg =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        'Error al registrar. Por favor verifica los datos e intenta de nuevo.';
      setApiError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F5F5] flex items-center justify-center px-4 py-12">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-6">
          <div className="bg-[#2B3E59] rounded-full p-3 mb-3">
            <HeartPulse size={28} color="white" />
          </div>
          <h1 className="font-inter text-2xl font-bold text-[#2B3E59]">Crear Cuenta</h1>
          <p className="text-gray-500 text-sm mt-1">EPS Digital</p>
        </div>

        {/* Step Indicator */}
        <div className="flex items-center gap-3 mb-6">
          {[1, 2].map((s) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0
                  ${s < step ? 'bg-green-500 text-white' : s === step ? 'bg-[#2B3E59] text-white' : 'bg-gray-200 text-gray-500'}`}
              >
                {s < step ? <CheckCircle2 size={16} /> : s}
              </div>
              <span className={`text-xs ${s === step ? 'text-[#2B3E59] font-medium' : 'text-gray-400'}`}>
                {s === 1 ? 'Datos personales' : 'Contacto y acceso'}
              </span>
              {s < 2 && <div className="flex-1 h-px bg-gray-200" />}
            </div>
          ))}
        </div>

        {apiError && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-red-600 text-sm">{apiError}</p>
          </div>
        )}

        {/* Step 1 */}
        {step === 1 && (
          <form onSubmit={form1.handleSubmit(onStep1)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de documento *</label>
              <select
                {...form1.register('tipo_documento', { required: 'Requerido' })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
              >
                {TIPO_DOC_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Número de documento *</label>
              <input
                {...form1.register('numero_documento', {
                  required: 'Requerido',
                  minLength: { value: 5, message: 'Mínimo 5 caracteres' },
                })}
                type="text"
                placeholder="Ej: 1234567890"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
              />
              {form1.formState.errors.numero_documento && (
                <p className="text-red-500 text-xs mt-1">{form1.formState.errors.numero_documento.message}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombres *</label>
                <input
                  {...form1.register('nombres', { required: 'Requerido' })}
                  type="text"
                  placeholder="Ej: Juan Carlos"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                />
                {form1.formState.errors.nombres && (
                  <p className="text-red-500 text-xs mt-1">{form1.formState.errors.nombres.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Apellidos *</label>
                <input
                  {...form1.register('apellidos', { required: 'Requerido' })}
                  type="text"
                  placeholder="Ej: Pérez García"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
                />
                {form1.formState.errors.apellidos && (
                  <p className="text-red-500 text-xs mt-1">{form1.formState.errors.apellidos.message}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fecha de nacimiento *</label>
              <input
                {...form1.register('fecha_nacimiento', { required: 'Requerido' })}
                type="date"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
              />
              {form1.formState.errors.fecha_nacimiento && (
                <p className="text-red-500 text-xs mt-1">{form1.formState.errors.fecha_nacimiento.message}</p>
              )}
            </div>

            <div className="flex items-start gap-2">
              <input
                {...form1.register('acepta_terminos')}
                type="checkbox"
                id="terminos"
                className="mt-0.5 accent-[#2B3E59]"
              />
              <label htmlFor="terminos" className="text-sm text-gray-600 cursor-pointer">
                Acepto los{' '}
                <button type="button" className="text-[#2B3E59] font-medium hover:underline">
                  términos y condiciones
                </button>{' '}
                y la política de privacidad
              </label>
            </div>
            {form1.formState.errors.acepta_terminos && (
              <p className="text-red-500 text-xs">{form1.formState.errors.acepta_terminos.message}</p>
            )}

            <button
              type="submit"
              className="w-full bg-[#2B3E59] text-white font-semibold py-3 rounded-lg hover:bg-[#1e2d40] transition-colors"
            >
              Siguiente →
            </button>
          </form>
        )}

        {/* Step 2 */}
        {step === 2 && (
          <form onSubmit={form2.handleSubmit(onStep2)} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono / Celular *</label>
              <input
                {...form2.register('telefono', {
                  required: 'Requerido',
                  pattern: { value: /^[0-9+\-\s]{7,15}$/, message: 'Número de teléfono inválido' },
                })}
                type="tel"
                placeholder="Ej: 3001234567"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
              />
              {form2.formState.errors.telefono && (
                <p className="text-red-500 text-xs mt-1">{form2.formState.errors.telefono.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Correo electrónico *</label>
              <input
                {...form2.register('correo', {
                  required: 'Requerido',
                  pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Correo inválido' },
                })}
                type="email"
                placeholder="correo@ejemplo.com"
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59]"
              />
              {form2.formState.errors.correo && (
                <p className="text-red-500 text-xs mt-1">{form2.formState.errors.correo.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña *</label>
              <div className="relative">
                <input
                  {...form2.register('password', {
                    required: 'Requerido',
                    minLength: { value: 8, message: 'Mínimo 8 caracteres' },
                  })}
                  type={showPass ? 'text' : 'password'}
                  placeholder="Mínimo 8 caracteres"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59] pr-10"
                />
                <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {form2.formState.errors.password && (
                <p className="text-red-500 text-xs mt-1">{form2.formState.errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar contraseña *</label>
              <div className="relative">
                <input
                  {...form2.register('confirm_password', { required: 'Requerido' })}
                  type={showConfirm ? 'text' : 'password'}
                  placeholder="Repite tu contraseña"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 focus:border-[#2B3E59] pr-10"
                />
                <button type="button" onClick={() => setShowConfirm(!showConfirm)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                  {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {form2.formState.errors.confirm_password && (
                <p className="text-red-500 text-xs mt-1">{form2.formState.errors.confirm_password.message}</p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex items-center gap-1 border border-gray-300 text-gray-600 font-medium py-3 px-4 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <ChevronLeft size={16} /> Volver
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 bg-[#2B3E59] text-white font-semibold py-3 rounded-lg hover:bg-[#1e2d40] transition-colors disabled:opacity-60"
              >
                {loading ? 'Registrando...' : 'Registrarme'}
              </button>
            </div>
          </form>
        )}

        <p className="text-center text-sm text-gray-500 mt-6">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-[#2B3E59] font-medium hover:underline">
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
