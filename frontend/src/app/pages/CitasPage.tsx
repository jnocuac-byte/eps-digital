import { NavLink, Outlet } from 'react-router';
import { CalendarPlus, CalendarCheck, RotateCcw, History } from 'lucide-react';

const tabs = [
  { to: '/citas/agendar', label: 'Agendar Cita', icon: <CalendarPlus size={16} /> },
  { to: '/citas/ver', label: 'Ver Citas', icon: <CalendarCheck size={16} /> },
  { to: '/citas/cancelar', label: 'Cancelar / Reprogramar', icon: <RotateCcw size={16} /> },
  { to: '/citas/historial', label: 'Historial', icon: <History size={16} /> },
];

export default function CitasPage() {
  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      {/* Tab Navigation */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 mb-6 overflow-hidden">
        <div className="flex overflow-x-auto scrollbar-hide">
          {tabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-5 py-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors
                ${isActive
                  ? 'border-[#2B3E59] text-[#2B3E59] bg-blue-50/50'
                  : 'border-transparent text-gray-500 hover:text-[#2B3E59] hover:bg-gray-50'}`
              }
            >
              {tab.icon}
              {tab.label}
            </NavLink>
          ))}
        </div>
      </div>

      <Outlet />
    </div>
  );
}
