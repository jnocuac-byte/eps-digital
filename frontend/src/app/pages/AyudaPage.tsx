import { useState } from 'react';
import {
  HelpCircle, ChevronDown, ChevronUp, Mail, BookOpen,
  Shield, Users, Calendar, AlertCircle, Key, XCircle
} from 'lucide-react';

const STEPS = [
  { num: 1, title: 'Regístrate', desc: 'Crea tu cuenta con tu documento de identidad y datos personales.' },
  { num: 2, title: 'Inicia Sesión', desc: 'Accede con tu tipo de documento, número y contraseña.' },
  { num: 3, title: 'Explora Servicios', desc: 'Revisa los servicios médicos disponibles para tu tipo de afiliación.' },
  { num: 4, title: 'Agenda una Cita', desc: 'Ve a Citas Médicas → Agendar, selecciona servicio, fecha y hora.' },
  { num: 5, title: 'Confirma', desc: 'Revisa el resumen y confirma. Recibirás una notificación de confirmación.' },
];

const FAQS = [
  {
    q: '¿Cómo agendar una cita?',
    a: 'Inicia sesión en tu cuenta, ve a "Citas Médicas" en el menú superior, selecciona "Agendar nueva cita", elige el servicio, especialidad, médico, fecha y hora preferida, describe tus síntomas y confirma.',
    icon: <Calendar size={16} />,
  },
  {
    q: '¿Necesito registrarme para usar la plataforma?',
    a: 'Sí, necesitas una cuenta de afiliado activa. El registro es gratuito y solo requiere tu documento de identidad y datos básicos. Puedes ver los servicios disponibles sin registrarte.',
    icon: <Users size={16} />,
  },
  {
    q: '¿Qué significa el asterisco (*) en los formularios?',
    a: 'El asterisco (*) indica que el campo es obligatorio y debe ser llenado para continuar con el proceso. Sin estos datos no es posible procesar tu solicitud.',
    icon: <AlertCircle size={16} />,
  },
  {
    q: '¿Cómo cancelar una cita?',
    a: 'Ve a "Citas Médicas" → "Cancelar o Reprogramar". Selecciona la cita que deseas cancelar, elige un motivo (opcional) y confirma la cancelación. Puedes hacer esto hasta 2 horas antes de la cita.',
    icon: <XCircle size={16} />,
  },
  {
    q: '¿Qué hago si olvido mi contraseña?',
    a: 'En la página de inicio de sesión, haz clic en "¿Olvidaste tu contraseña?". Ingresa tu correo electrónico registrado y recibirás un enlace para restablecerla. Si no tienes acceso al correo, contacta a soporte.',
    icon: <Key size={16} />,
  },
  {
    q: '¿Puedo usar el Asistente Virtual sin iniciar sesión?',
    a: 'El Asistente Virtual EPSIA requiere que estés autenticado para brindarte una atención personalizada basada en tu historial médico y afiliación. Sin embargo, puedes ver la información general de servicios sin sesión.',
    icon: <HelpCircle size={16} />,
  },
];

const CONTACTS = [
  { name: 'Andrés Ramos', email: 'andres.ramos@epsdigital.com', role: 'Soporte Técnico' },
  { name: 'Juan Esteban Nocua', email: 'juan.nocua@epsdigital.com', role: 'Atención al Usuario' },
  { name: 'Santiago Pardo', email: 'santiago.pardo@epsdigital.com', role: 'Administración' },
];

function FAQItem({ faq }: { faq: typeof FAQS[0] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className="text-[#2B3E59]">{faq.icon}</span>
          <span className="font-medium text-gray-800 text-sm">{faq.q}</span>
        </div>
        {open ? (
          <ChevronUp size={16} className="text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronDown size={16} className="text-gray-400 flex-shrink-0" />
        )}
      </button>
      {open && (
        <div className="px-5 py-4 bg-blue-50/50 border-t border-gray-100">
          <p className="text-gray-600 text-sm leading-relaxed">{faq.a}</p>
        </div>
      )}
    </div>
  );
}

export default function AyudaPage() {
  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-10">
      {/* Header */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center justify-center bg-[#2B3E59] rounded-full p-4 mb-4">
          <HelpCircle size={32} className="text-white" />
        </div>
        <h1 className="font-inter text-3xl md:text-4xl font-bold text-[#2B3E59] mb-3">
          Centro de Ayuda
        </h1>
        <p className="text-gray-500 max-w-xl mx-auto">
          Encuentra respuestas a tus preguntas y aprende a usar EPS Digital de forma eficiente.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Guía de Uso */}
        <section>
          <div className="flex items-center gap-2 mb-5">
            <BookOpen size={20} className="text-[#2B3E59]" />
            <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Guía de Uso</h2>
          </div>
          <div className="space-y-3">
            {STEPS.map((step) => (
              <div key={step.num} className="flex gap-4 bg-white rounded-xl border border-gray-100 shadow-sm p-4">
                <div className="w-8 h-8 rounded-full bg-[#2B3E59] text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                  {step.num}
                </div>
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{step.title}</p>
                  <p className="text-gray-500 text-sm mt-0.5">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Preguntas Frecuentes */}
        <section>
          <div className="flex items-center gap-2 mb-5">
            <HelpCircle size={20} className="text-[#2B3E59]" />
            <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Preguntas Frecuentes</h2>
          </div>
          <div className="space-y-3">
            {FAQS.map((faq) => (
              <FAQItem key={faq.q} faq={faq} />
            ))}
          </div>
        </section>
      </div>

      {/* Contact & Legal */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-10">
        {/* Contacto */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-5">
            <Mail size={20} className="text-[#2B3E59]" />
            <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Contacto y Soporte</h2>
          </div>
          <p className="text-gray-500 text-sm mb-5">
            ¿No encontraste lo que buscabas? Contáctanos directamente:
          </p>
          <div className="space-y-4">
            {CONTACTS.map((c) => (
              <div key={c.email} className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                <div className="w-9 h-9 rounded-full bg-[#2B3E59] text-white flex items-center justify-center flex-shrink-0">
                  <Users size={16} />
                </div>
                <div>
                  <p className="font-medium text-gray-800 text-sm">{c.name}</p>
                  <p className="text-gray-400 text-xs">{c.role}</p>
                  <a
                    href={`mailto:${c.email}`}
                    className="text-[#2B3E59] text-xs hover:underline"
                  >
                    {c.email}
                  </a>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-xl">
            <p className="text-sm text-gray-600">
              <strong>Email general:</strong>{' '}
              <a href="mailto:correo@epsdigital.com" className="text-[#2B3E59] hover:underline">
                correo@epsdigital.com
              </a>
            </p>
          </div>
        </section>

        {/* Legal */}
        <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-5">
            <Shield size={20} className="text-[#2B3E59]" />
            <h2 className="font-inter text-xl font-bold text-[#2B3E59]">Información Legal</h2>
          </div>
          <div className="space-y-3 text-sm text-gray-600">
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-xl">
              <p className="font-medium text-yellow-800 mb-1">⚠️ Aviso Importante</p>
              <p className="text-yellow-700 text-sm">
                Esta es una plataforma funcional para demostración académica. Los datos son simulados.
              </p>
            </div>
            <div className="space-y-2">
              <p className="flex gap-2">
                <span className="text-[#2B3E59] font-medium flex-shrink-0">Proyecto:</span>
                Prototipo funcional - Práctica de Ingeniería III
              </p>
              <p className="flex gap-2">
                <span className="text-[#2B3E59] font-medium flex-shrink-0">Institución:</span>
                Universidad Central
              </p>
              <p className="flex gap-2">
                <span className="text-[#2B3E59] font-medium flex-shrink-0">Normativa:</span>
                Ley 1581 de 2012 (Protección de Datos Personales)
              </p>
              <p className="flex gap-2">
                <span className="text-[#2B3E59] font-medium flex-shrink-0">Datos:</span>
                Simulados — no se almacena información sensible real
              </p>
              <p className="flex gap-2">
                <span className="text-[#2B3E59] font-medium flex-shrink-0">Año:</span>
                2026
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
