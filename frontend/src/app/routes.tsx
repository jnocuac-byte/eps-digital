import { createBrowserRouter, Navigate } from 'react-router';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';

import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ProfilePage from './pages/ProfilePage';
import CitasPage from './pages/CitasPage';
import AgendarCitaPage from './pages/AgendarCitaPage';
import VerCitasPage from './pages/VerCitasPage';
import CancelarCitaPage from './pages/CancelarCitaPage';
import HistorialCitasPage from './pages/HistorialCitasPage';
import AsistentePage from './pages/AsistentePage';
import ServiciosPage from './pages/ServiciosPage';
import AyudaPage from './pages/AyudaPage';
import NotFoundPage from './pages/NotFoundPage';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: Layout,
    children: [
      { index: true, Component: HomePage },
      { path: 'login', Component: LoginPage },
      { path: 'register', Component: RegisterPage },
      { path: 'servicios', Component: ServiciosPage },
      { path: 'ayuda', Component: AyudaPage },
      {
        path: 'perfil',
        element: (
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        ),
      },
      {
        path: 'citas',
        element: (
          <ProtectedRoute>
            <CitasPage />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <Navigate to="agendar" replace /> },
          { path: 'agendar', Component: AgendarCitaPage },
          { path: 'ver', Component: VerCitasPage },
          { path: 'cancelar', Component: CancelarCitaPage },
          { path: 'historial', Component: HistorialCitasPage },
        ],
      },
      {
        path: 'asistente',
        element: (
          <ProtectedRoute>
            <AsistentePage />
          </ProtectedRoute>
        ),
      },
      { path: '*', Component: NotFoundPage },
    ],
  },
]);
