import { Link, useLocation } from 'react-router';
import {
  BarChart2, Users, Settings, FileText, Shield, LogOut, HeartPulse,
} from 'lucide-react';
import { useAuthStore } from '../stores/authStore';

const PRIMARY = '#2B3E59';

const navItems = [
  { to: '/admin', label: 'Dashboard', icon: <BarChart2 size={18} /> },
  { to: '/admin/medicos', label: 'Médicos', icon: <Users size={18} /> },
  { to: '/admin/servicios', label: 'Servicios', icon: <Settings size={18} /> },
  { to: '/admin/reportes', label: 'Reportes', icon: <FileText size={18} /> },
];

export function AdminLayout({ children }: { children: React.ReactNode }) {
  const { logout, esSuperAdmin } = useAuthStore();
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside
        className="w-64 flex-shrink-0 flex flex-col"
        style={{ backgroundColor: PRIMARY }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-white/10">
          <div className="bg-white rounded-full p-2">
            <HeartPulse size={18} color={PRIMARY} />
          </div>
          <div>
            <p className="text-white font-semibold text-sm">EPS Digital</p>
            <p className="text-white/60 text-xs">Panel Admin</p>
          </div>
        </div>

        {/* Nav */}
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

          {esSuperAdmin && (
            <Link
              to="/admin/admins"
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === '/admin/admins'
                  ? 'bg-white/20 text-white'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`}
            >
              <Shield size={18} />
              Gestión Admins
            </Link>
          )}
        </nav>

        {/* Logout */}
        <div className="px-3 py-4 border-t border-white/10">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-3 py-2.5 w-full rounded-lg text-sm font-medium text-white/70 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut size={18} />
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}