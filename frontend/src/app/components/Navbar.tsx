import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router';
import {
  HeartPulse, Menu, X, Calendar, Clock, RotateCcw, History,
  ChevronDown, LogOut, User
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

const PRIMARY = '#2B3E59';

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [citasOpen, setCitasOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const citasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMobileOpen(false);
    setCitasOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (citasRef.current && !citasRef.current.contains(e.target as Node)) {
        setCitasOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const citasItems = [
    { to: '/citas/agendar', label: 'Agendar nueva cita', icon: <Calendar size={16} /> },
    { to: '/citas/ver', label: 'Ver citas programadas', icon: <Clock size={16} /> },
    { to: '/citas/cancelar', label: 'Cancelar o Reprogramar', icon: <RotateCcw size={16} /> },
    { to: '/citas/historial', label: 'Historial de citas', icon: <History size={16} /> },
  ];

  const navLinks = [
    { to: '/', label: 'Inicio' },
    { to: '/perfil', label: 'Mi Perfil', private: true },
    { to: '/asistente', label: 'Asistente Virtual', private: true },
    { to: '/servicios', label: 'Servicios' },
    { to: '/ayuda', label: 'Ayuda' },
  ];

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 shadow-md"
      style={{ backgroundColor: PRIMARY }}
    >
      <div className="max-w-[1440px] mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 flex-shrink-0">
            <div className="bg-white rounded-full p-1.5">
              <HeartPulse size={20} color={PRIMARY} />
            </div>
            <span className="text-white font-inter font-semibold text-lg">EPS Digital</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden lg:flex items-center gap-6">
            {navLinks.map((link) => {
              if (link.private && !isAuthenticated) return null;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className="text-white hover:text-blue-200 transition-colors text-sm font-medium"
                >
                  {link.label}
                </Link>
              );
            })}

            {/* Citas Dropdown */}
            <div className="relative" ref={citasRef}>
              <button
                onClick={() => setCitasOpen(!citasOpen)}
                className="flex items-center gap-1 text-white hover:text-blue-200 transition-colors text-sm font-medium"
              >
                Citas Médicas
                <ChevronDown size={14} className={`transition-transform ${citasOpen ? 'rotate-180' : ''}`} />
              </button>
              {citasOpen && (
                <div className="absolute top-full left-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-2 z-50">
                  {citasItems.map((item) => (
                    <Link
                      key={item.to}
                      to={item.to}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-sm text-gray-700"
                    >
                      <span className="text-[#2B3E59]">{item.icon}</span>
                      {item.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Auth Buttons */}
          <div className="hidden lg:flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <Link to="/perfil" className="flex items-center gap-1.5 text-white hover:text-blue-200 transition-colors text-sm">
                  <User size={16} />
                  <span>{user?.nombres?.split(' ')[0] || 'Mi perfil'}</span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 text-white border border-white/50 rounded-full px-4 py-1.5 hover:bg-white hover:text-[#2B3E59] transition-colors text-sm"
                >
                  <LogOut size={14} />
                  Cerrar Sesión
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="border border-white text-white rounded-full px-4 py-1.5 text-sm hover:bg-white hover:text-[#2B3E59] transition-colors"
                >
                  Iniciar Sesión
                </Link>
                <Link
                  to="/register"
                  className="bg-white text-[#2B3E59] rounded-full px-4 py-1.5 text-sm font-semibold hover:bg-blue-50 transition-colors"
                >
                  Registrarse
                </Link>
              </>
            )}
          </div>

          {/* Mobile Hamburger */}
          <button
            className="lg:hidden text-white p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="lg:hidden bg-[#1e2d40] border-t border-white/10">
          <div className="px-4 py-4 space-y-1">
            {navLinks.map((link) => {
              if (link.private && !isAuthenticated) return null;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className="block py-2.5 text-white hover:text-blue-200 transition-colors text-sm"
                >
                  {link.label}
                </Link>
              );
            })}
            <div className="py-1">
              <p className="text-white/60 text-xs uppercase tracking-wide mb-2">Citas Médicas</p>
              {citasItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="flex items-center gap-2 py-2 text-white/90 hover:text-white transition-colors text-sm pl-2"
                >
                  {item.icon} {item.label}
                </Link>
              ))}
            </div>
            <div className="pt-3 border-t border-white/20 flex flex-col gap-2">
              {isAuthenticated ? (
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-white text-sm py-2"
                >
                  <LogOut size={16} /> Cerrar Sesión
                </button>
              ) : (
                <>
                  <Link to="/login" className="block text-white text-sm py-2">Iniciar Sesión</Link>
                  <Link to="/register" className="block text-white text-sm py-2">Registrarse</Link>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
