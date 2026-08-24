import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import { useAuthStore } from '../stores/authStore';

interface RoleRouteProps {
  children: ReactNode;
  allowedRoles: ('admin' | 'medico')[];
}

/** Protege rutas por rol. Redirige a /login si no está autenticado, o a / si no tiene el rol requerido. */
export function RoleRoute({ children, allowedRoles }: RoleRouteProps) {
  const { isAuthenticated, rol } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!rol || !allowedRoles.includes(rol as 'admin' | 'medico')) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
