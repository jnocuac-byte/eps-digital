import { useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router';
import { Calendar, Bot, MapPin, ArrowRight, MessageCircle, Clock } from 'lucide-react';
import { useAuthStore } from '../stores/authStore';
import { useQuery } from '@tanstack/react-query';
import { citasApi } from '../lib/apiClient';
import { parseFechaLocal } from '../lib/fechas';

const HERO_DOCTOR = '/images/hero-medico.webp';

const benefits = [
  {
    icon: <Calendar size={36} className="text-[#2B3E59]" />,
    title: 'Agenda 24/7',
    desc: 'Reserva y gestiona tus citas a cualquier hora, desde cualquier lugar',
  },
  {
    icon: <Bot size={36} className="text-[#2B3E59]" />,
    title: 'Asistente con IA',
    desc: 'Obtén respuestas rápidas y orientación médica personalizada',
  },
  {
    icon: <MapPin size={36} className="text-[#2B3E59]" />,
    title: 'Cerca de ti',
    desc: 'Encuentra especialistas y centros cercanos a tu ubicación',
  },
];

export default function HomePage() {
  const { isAuthenticated, user, userId, rol } = useAuthStore();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    if (isAuthenticated && rol === 'medico') {
      navigate('/medico/dashboard', { replace: true });
    }
  }, [isAuthenticated, rol, navigate]);

  const { data: citasData } = useQuery({
    queryKey: ['citas', userId],
    queryFn: () => citasApi.getByUser(userId!).then((r) => r.data),
    enabled: isAuthenticated && !!userId,
  });

  const proxima = citasData?.find?.(
    (c: { estado: string }) => c.estado === 'programada'
  );

  return (
    <div>
      {/* Hero */}
      <section
        className="relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #1a2e45 0%, #2B3E59 58%, #466b79 100%)' }}
      >
        <div className="max-w-[1440px] mx-auto px-6 py-16 md:py-24 flex flex-col md:flex-row items-center gap-12">
          <div className="flex-1 text-white">
            {isAuthenticated && user ? (
              <div className="mb-6 bg-white/10 rounded-2xl p-5 border border-white/20 max-w-sm shadow-lg">
                <p className="text-white/80 text-sm mb-1">¡Bienvenido de vuelta!</p>
                <p className="text-white text-lg font-semibold font-inter">
                  {user.nombres} {user.apellidos}
                </p>
                <p className="text-white/70 text-sm">Documento: {user.tipo_documento} {user.numero_documento}</p>
                <span className="inline-block mt-2 bg-green-400/20 text-green-300 text-xs px-2 py-0.5 rounded-full">
                  Estado: Activo
                </span>
              </div>
            ) : null}
            <h1 className="font-inter text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
              Agenda tu cita médica de{' '}
              <span className="text-teal-100">forma rápida</span> y sencilla
            </h1>
            <p className="text-white/80 text-lg mb-8">
              Inteligencia Artificial al servicio de tu salud
            </p>
            <div className="flex flex-wrap gap-4">
              <Link
                to="/citas/agendar"
                className="bg-white text-[#2B3E59] font-semibold px-7 py-3 rounded-xl shadow-sm hover:bg-teal-50 hover:-translate-y-0.5 transition-all"
              >
                Agendar Cita
              </Link>
              <Link
                to="/servicios"
                className="border border-white/70 text-white font-semibold px-7 py-3 rounded-xl hover:bg-white hover:text-[#2B3E59] transition-all"
              >
                Conoce más
              </Link>
            </div>
            {isAuthenticated && (
              <div className="flex gap-3 mt-6">
                <Link
                  to="/perfil"
                  className="flex items-center gap-1.5 text-white/80 hover:text-white text-sm transition-colors"
                >
                  <ArrowRight size={14} /> Ir a mi perfil
                </Link>
                <span className="text-white/40">|</span>
                <Link
                  to="/citas/ver"
                  className="flex items-center gap-1.5 text-white/80 hover:text-white text-sm transition-colors"
                >
                  <ArrowRight size={14} /> Ver mis citas
                </Link>
              </div>
            )}
          </div>
          <div className="relative flex-shrink-0 w-full md:w-[430px] lg:w-[520px] h-[340px] md:h-[440px] lg:h-[500px]">
            <img
              src={HERO_DOCTOR}
              alt="Médico profesional"
              className="absolute inset-0 w-full h-full object-contain rounded-none scale-[1.16] md:scale-[1.2] lg:scale-[1.22]"
            />
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#2B3E59]" />
      </section>

      {/* Próxima Cita (si autenticado) */}
      {isAuthenticated && (
        <section className="max-w-[1440px] mx-auto px-6 py-6">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 md:p-7">
            <div className="flex items-center gap-2 mb-3">
              <Clock size={18} className="text-[#2B3E59]" />
              <h3 className="font-inter font-semibold text-[#2B3E59]">Próxima Cita</h3>
            </div>
            {proxima ? (
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <p className="font-medium text-gray-800">{proxima.tipo_servicio || proxima.especialidad_nombre}</p>
                  <p className="text-gray-500 text-sm">{proxima.medico_nombre && `Dr. ${proxima.medico_nombre}`}</p>
                  <p className="text-gray-500 text-sm">
                    {parseFechaLocal(proxima.fecha_cita).toLocaleDateString('es-CO', {
                      weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                    })} · {proxima.hora_inicio}
                  </p>
                </div>
                <Link
                  to="/citas/ver"
                  className="bg-[#2B3E59] text-white px-5 py-2.5 rounded-xl text-sm hover:bg-[#1e2d40] hover:-translate-y-0.5 transition-all"
                >
                  Ver detalles
                </Link>
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <p className="text-gray-500 text-sm">
                  Aún no tienes citas guardadas. Puedes agendar una desde el menú principal.
                </p>
                <Link
                  to="/citas/agendar"
                  className="bg-[#2B3E59] text-white px-5 py-2.5 rounded-xl text-sm hover:bg-[#1e2d40] hover:-translate-y-0.5 transition-all whitespace-nowrap"
                >
                  Agendar ahora
                </Link>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Beneficios */}
      <section className="max-w-[1440px] mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {benefits.map((b) => (
            <div
              key={b.title}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center hover:shadow-md hover:-translate-y-0.5 transition-all"
            >
              <div className="flex justify-center mb-4">{b.icon}</div>
              <h3 className="font-inter font-semibold text-[#2B3E59] text-lg mb-3">{b.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{b.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Section */}
      <section className="max-w-[1440px] mx-auto px-6 pb-12">
        <div
          className="rounded-3xl p-10 text-center text-white shadow-md"
          style={{ background: 'linear-gradient(135deg, #2B3E59, #466b79)' }}
        >
          <h2 className="font-inter text-2xl md:text-3xl font-bold mb-3">
            ¿Necesitas orientación médica rápida?
          </h2>
          <p className="text-white/80 mb-6 text-lg">
            Nuestro Asistente Virtual EPSIA está disponible 24/7 para ayudarte.
          </p>
          <Link
            to="/asistente"
            className="inline-flex items-center gap-2 bg-white text-[#2B3E59] font-semibold px-8 py-3 rounded-xl hover:bg-teal-50 hover:-translate-y-0.5 transition-all"
          >
            <MessageCircle size={18} />
            Hablar con EPSIA
          </Link>
        </div>
      </section>

      {/* Floating Chat Button */}
      {pathname !== '/' && (
        <Link
          to="/asistente"
          className="fixed bottom-6 right-6 bg-[#2B3E59] text-white p-4 rounded-2xl shadow-lg hover:bg-[#1e2d40] hover:-translate-y-1 transition-all z-40 flex items-center gap-2"
          title="Asistente Virtual"
        >
          <Bot size={22} />
          <span className="hidden sm:block text-sm font-medium">EPSIA</span>
        </Link>
      )}
    </div>
  );
}