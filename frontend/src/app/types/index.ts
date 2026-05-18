export interface User {
  usuario_id: string;
  nombres: string;
  apellidos: string;
  tipo_documento: string;
  numero_documento: string;
  fecha_nacimiento: string;
  correo: string;
  telefono: string;
  creado_en?: string;
  actualizado_en?: string;
}

export interface InformacionMedica {
  tipo_sangre?: string;
  alergias?: string;
  enfermedades_cronicas?: string;
  medico_asignado?: string;
}

export interface Afiliacion {
  numero_poliza?: string;
  fecha_afiliacion?: string;
  estado?: string;
  tipo_afiliacion?: string;
}

export interface UserCompleto {
  user: User;
  informacion_medica: InformacionMedica;
  afiliacion: Afiliacion;
}

export interface Cita {
  cita_id: string;
  usuario_id: string;
  medico_id?: string;
  especialidad_id?: string;
  tipo_servicio: string;
  fecha_cita: string;
  hora_inicio: string;
  hora_fin?: string;
  sede_id?: string;
  descripcion_sintomas?: string;
  estado: 'programada' | 'cancelada' | 'atendida' | 'no_asistio';
  especialidad_nombre?: string;
  medico_nombre?: string;
  sede_nombre?: string;
  creado_en?: string;
}

export interface Servicio {
  servicio_id: string;
  nombre: string;
  descripcion: string;
  activo?: boolean;
  disponible?: boolean;
  icono?: string;
}

export interface Especialidad {
  especialidad_id: string;
  nombre: string;
  servicio_id: string;
  duracion_cita_minutos?: number;
}

export interface Medico {
  medico_id: string;
  nombres: string;
  apellidos: string;
  especialidad_id: string;
  especialidad_nombre?: string;
}

export interface AuthCredentials {
  access_token: string;
  refresh_token: string;
  token_type: string;
  usuario_id: string;
  requiere_2fa?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  action?: string;
}

export interface Sede {
  sede_id: string;
  nombre: string;
  direccion: string;
  ciudad: string;
  telefono?: string;
  activo?: boolean;
}

export interface Disponibilidad {
  disponibilidad_id: string;
  medico_id: string;
  especialidad_id: string;
  sede_id: string;
  dia_semana: number;
  hora_inicio: string;
  hora_fin: string;
  activo?: boolean;
}
