import axios from 'axios';
import { useAuthStore } from '../stores/authStore';

const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

const BASE_URLS = {
  auth: isLocal ? 'http://localhost:8001' : 'https://eps-digital.onrender.com',
  user: isLocal ? 'http://localhost:8002' : 'https://eps-user-service.onrender.com',
  citas: isLocal ? 'http://localhost:8003' : 'https://eps-appointments-service.onrender.com',
  catalogo: isLocal ? 'http://localhost:8004' : 'https://eps-catalog-service.onrender.com',
  ai: isLocal ? 'http://localhost:8005' : 'https://eps-ainlp-service.onrender.com',
  notifications: isLocal ? 'http://localhost:8006' : 'https://eps-notification-service.onrender.com',
};

function createClient(baseURL: string, requiresAuth = false) {
  const client = axios.create({
    baseURL,
    headers: { 'Content-Type': 'application/json' },
    timeout: 15000,
  });

  if (requiresAuth) {
    client.interceptors.request.use((config) => {
      const token = useAuthStore.getState().token;
      const userId = useAuthStore.getState().userId;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      if (userId) {
        config.headers['X-User-ID'] = userId;
      }
      return config;
    });

    client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          useAuthStore.getState().logout();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  return client;
}

export const authClient = createClient(BASE_URLS.auth);
export const userClient = createClient(BASE_URLS.user, true);
export const citasClient = createClient(BASE_URLS.citas, true);
export const catalogoClient = createClient(BASE_URLS.catalogo, true);
export const aiClient = createClient(BASE_URLS.ai, true);
export const notificacionesClient = createClient(BASE_URLS.notifications, true);

// Auth API
export const authApi = {
  login: (data: { tipo_documento: string; numero_documento: string; password: string }) =>
    authClient.post('/auth/login/documento', data),
  register: (data: Record<string, unknown>) =>
    authClient.post('/auth/register', data),
  me: () => authClient.get('/auth/me'),
  getMedicoId: () => authClient.get('/auth/medico-id'),
};

// User API
export const userApi = {
  create: (data: Record<string, unknown>) =>
    userClient.post('/usuarios', data),
  getById: (userId: string) =>
    userClient.get(`/usuarios/${userId}`),
  update: (userId: string, data: Record<string, unknown>) =>
    userClient.put(`/usuarios/${userId}`, data),
  getCompleto: (userId: string) =>
    userClient.get(`/usuarios/${userId}/completo`),
  buscarPorDocumento: (tipoDocumento: string, numeroDocumento: string) =>
    userClient.get('/usuarios/buscar', { params: { tipo_documento: tipoDocumento, numero_documento: numeroDocumento } }),
};

// Citas API
export const citasApi = {
  create: (data: Record<string, unknown>) =>
    citasClient.post('/citas', data),
  getByUser: (userId: string) =>
    citasClient.get(`/citas/usuario/${userId}`),
  getHistorial: (userId: string) =>
    citasClient.get(`/citas/usuario/${userId}/historial`),
  cancel: (citaId: string, motivo: string) =>
    citasClient.post(`/citas/${citaId}/cancelar`, { motivo }),
  getById: (citaId: string) =>
    citasClient.get(`/citas/${citaId}`),
  reprogramar: (citaId: string, data: { nueva_fecha: string; nueva_hora_inicio: string; nueva_hora_fin: string; motivo?: string }) =>
    citasClient.post(`/citas/${citaId}/reprogramar`, data),
  getSlotsDisponibles: (params: {
    medico_id?: string;
    servicio_id?: string;
    especialidad_id?: string;
    fecha: string;
  }) =>
    citasClient.get('/citas/slots-disponibles', { params }),
  getCitasMedico: (medicoId: string, filters?: { fecha?: string; fecha_inicio?: string; fecha_fin?: string }) =>
    citasClient.get(`/citas/medico/${medicoId}`, { params: filters }),
  getMetricasMedico: (medicoId: string) =>
    citasClient.get(`/citas/medico/${medicoId}/metricas`),
  updateEstado: (citaId: string, estado: string) =>
    citasClient.patch(`/citas/${citaId}/estado`, { estado }),
};

// Catálogo API
export const catalogoApi = {
  getServicios: () =>
    catalogoClient.get('/servicios'),
  getEspecialidades: (servicioId?: string) =>
    catalogoClient.get('/especialidades', { params: servicioId ? { servicio_id: servicioId } : {} }),
  getMedicos: (especialidadId?: string) =>
    catalogoClient.get('/medicos', { params: especialidadId ? { especialidad_id: especialidadId } : {} }),
  getMedicosDisponibles: (servicioId?: string, especialidadId?: string, fecha?: string, horaInicio?: string, horaFin?: string) =>
    catalogoClient.get('/medicos/disponibles', { 
      params: {
        ...(servicioId && { servicio_id: servicioId }),
        ...(especialidadId && { especialidad_id: especialidadId }),
        ...(fecha && { fecha }),
        ...(horaInicio && { hora_inicio: horaInicio }),
        ...(horaFin && { hora_fin: horaFin }),
      }
    }),
  getDisponibilidadesMedico: (medicoId: string) =>
    catalogoClient.get(`/disponibilidades/medico/${medicoId}`),
  getSedes: () =>
    catalogoClient.get('/sedes'),
};

// AI API
export const aiApi = {
  chat: (mensaje: string, conversacion_id?: string, usuario_id?: string) =>
    aiClient.post('/chat', {
      mensaje,
      ...(conversacion_id ? { conversacion_id } : {}),
      ...(usuario_id ? { usuario_id } : {}),
    }),
};

// Notificaciones API
export const notificacionesApi = {
  getByMedico: (medicoId: string) =>
    notificacionesClient.get(`/notificaciones/medico/${medicoId}`),
  marcarLeida: (id: string) =>
    notificacionesClient.patch(`/notificaciones/${id}/leida`),
  marcarTodasLeidas: (medicoId: string) =>
    notificacionesClient.patch(`/notificaciones/medico/${medicoId}/leer-todas`),
};
