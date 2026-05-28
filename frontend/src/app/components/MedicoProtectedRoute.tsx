import { Navigate } from 'react-router';
import { useAuthStore } from '../stores/authStore';

interface Props {
  children: React.ReactNode;
}

export function MedicoProtectedRoute({ children }: Props) {
  const { isAuthenticated, rol } = useAuthStore();

  if (!isAuthenticated) {
    return <Navigate to="/medico/login" replace />;
  }

  if (rol !== 'medico') {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
