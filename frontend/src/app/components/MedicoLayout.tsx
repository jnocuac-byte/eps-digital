import { Link, useLocation, Outlet } from 'react-router';
import { useState } from 'react';
import {
  Calendar, LayoutDashboard, HeartPulse, FileText, Bell, Stethoscope, Menu, X,
} from 'lucide-react';
import { MedicoProfileDropdown } from './medico/MedicoProfileDropdown';
import { NotificationBell } from './medico/NotificationBell';

const PRIMARY = '#2B3E59';

const navItems = [
  { to: '/medico/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
  { to: '/medico/agenda', label: 'Mi Agenda', icon: <Calendar size={18} /> },
  { to: '/medico/consultas', label: 'Consultas', icon: <Stethoscope size={18} /> },
  { to: '/medico/hce', label: 'Historias Clínicas', icon: <FileText size={18} /> },
  { to: '/medico/notificaciones', label: 'Notificaciones', icon: <Bell size={18} /> },
];

export function MedicoLayout() {
  const location = useLocation();
  const [menuAbierto, setMenuAbierto] = useState(false);

  return (
    <div className="flex min-h-screen bg-page-background">
      <aside
        className="hidden md:flex md:sticky md:top-0 md:h-screen w-60 flex-shrink-0 flex-col overflow-hidden shadow-lg"
        style={{ backgroundColor: PRIMARY }}
      >
        <div className="flex items-center gap-3 px-5 py-6 border-b border-white/10">
          <div className="bg-white rounded-2xl p-2 shadow-sm">
            <HeartPulse size={16} color={PRIMARY} />
          </div>
          <div>
            <p className="text-white font-semibold text-sm">EPS Digital</p>
            <p className="text-white/60 text-xs">Panel Médico</p>
          </div>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 py-5 space-y-1.5">
          {navItems.map((item) => {
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3.5 py-3 rounded-xl text-sm font-medium transition-[background-color,color,transform] duration-200 ${
                  isActive
                    ? 'bg-white text-[#2B3E59] shadow-sm'
                    : 'text-white/70 hover:bg-white/10 hover:text-white hover:translate-x-0.5'
                }`}
              >
                <span className={isActive ? 'text-[#2B3E59]' : 'text-white/70'}>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex-shrink-0 px-3 py-4 border-t border-white/10">
          <MedicoProfileDropdown />
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="relative h-[4.5rem] bg-white border-b border-gray-100 flex items-center justify-end px-4 md:px-6 flex-shrink-0 shadow-sm">
          <div className="absolute inset-y-0 left-4 flex items-center md:hidden">
            <button
              type="button"
              onClick={() => setMenuAbierto(true)}
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold text-[#2B3E59] transition-colors hover:bg-gray-100"
            >
              <Menu size={20} />
              <span>Menú</span>
            </button>
            <div className={`mobile-menu-overlay fixed inset-0 z-[100] bg-[#17253a]/40 transition-opacity duration-200 ${menuAbierto ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'}`}>
              <div
                className={`mobile-menu-panel fixed inset-y-0 left-0 flex w-[min(84vw,19rem)] flex-col text-white shadow-2xl transition-transform duration-300 ease-out ${menuAbierto ? 'translate-x-0' : '-translate-x-full'}`}
                style={{ backgroundColor: PRIMARY }}
              >
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-6">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-white p-2 shadow-sm">
                      <HeartPulse size={16} color={PRIMARY} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">EPS Digital</p>
                      <p className="text-xs text-white/60">Panel Médico</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMenuAbierto(false)}
                    className="rounded-xl p-2 text-white/75 hover:bg-white/10 hover:text-white"
                    aria-label="Cerrar menú"
                  >
                    <X size={20} />
                  </button>
                </div>
                <nav className="flex-1 space-y-1.5 overflow-y-auto px-3 py-5">
                  {navItems.map((item) => {
                    const isActive = location.pathname === item.to;
                    return (
                      <Link
                        key={item.to}
                        to={item.to}
                        onClick={() => setMenuAbierto(false)}
                        className={`flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-medium transition-colors ${
                          isActive
                            ? 'bg-white text-[#2B3E59] shadow-sm'
                            : 'text-white/70 hover:bg-white/10 hover:text-white'
                        }`}
                      >
                        <span className={isActive ? 'text-[#2B3E59]' : 'text-white/70'}>{item.icon}</span>
                        {item.label}
                      </Link>
                    );
                  })}
                </nav>
                <div className="border-t border-white/10 px-3 py-4">
                  <MedicoProfileDropdown />
                </div>
              </div>
            </div>
          </div>
          <NotificationBell />
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
