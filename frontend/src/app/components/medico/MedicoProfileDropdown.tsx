import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { ChevronDown, Settings, User, LogOut } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

export function MedicoProfileDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const initials = user
    ? `${user.nombres?.[0] || ''}${user.apellidos?.[0] || ''}`.toUpperCase()
    : 'DR';

  const handleLogout = () => {
    logout();
    navigate('/medico/login', { replace: true });
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-white/10 transition-colors"
      >
        <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center text-white text-sm font-semibold flex-shrink-0">
          {user?.nombres ? (
            <img
              src={`https://ui-avatars.com/api/?name=${user.nombres}+${user.apellidos}&background=fff&color=2B3E59&bold=true`}
              alt="Avatar"
              className="w-9 h-9 rounded-full"
            />
          ) : (
            initials
          )}
        </div>
        <div className="flex-1 text-left min-w-0">
          <p className="text-white text-sm font-medium truncate">
            Dr. {user?.nombres || 'Usuario'}
          </p>
        </div>
        <ChevronDown
          size={16}
          className={`text-white/70 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-lg shadow-lg border border-gray-100 py-1 z-50">
          <button
            onClick={() => {
              navigate('/medico/perfil');
              setOpen(false);
            }}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <User size={16} />
            Mi Perfil
          </button>
          <button
            onClick={() => {
              setOpen(false);
            }}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Settings size={16} />
            Configuración
          </button>
          <div className="border-t border-gray-100 my-1" />
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            <LogOut size={16} />
            Cerrar Sesión
          </button>
        </div>
      )}
    </div>
  );
}
