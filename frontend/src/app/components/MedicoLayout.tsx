import { Link, useLocation, Outlet } from 'react-router';
import {
  Calendar, LayoutDashboard, HeartPulse, FileText, Bell, Stethoscope,
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

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside
        className="w-56 flex-shrink-0 flex flex-col"
        style={{ backgroundColor: PRIMARY }}
      >
        <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
          <div className="bg-white rounded-full p-2">
            <HeartPulse size={16} color={PRIMARY} />
          </div>
          <div>
            <p className="text-white font-semibold text-sm">EPS Digital</p>
            <p className="text-white/60 text-xs">Panel Médico</p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.to;
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'text-white/70 hover:bg-white/10 hover:text-white'
                }`}
              >
                <span className={isActive ? 'text-white' : 'text-white/70'}>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="px-3 py-4 border-t border-white/10">
          <MedicoProfileDropdown />
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white border-b border-gray-100 flex items-center justify-end px-6 flex-shrink-0">
          <NotificationBell />
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
