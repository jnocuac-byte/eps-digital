import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Clock, User, Loader2 } from 'lucide-react';
import { authApi, citasApi, userApi } from '../../lib/apiClient';
import { useAuthStore } from '../../stores/authStore';

const TIPO_DOC_OPTIONS = [
  { value: 'CC', label: 'Cédula de Ciudadanía' },
  { value: 'CE', label: 'Cédula de Extranjería' },
  { value: 'PA', label: 'Pasaporte' },
  { value: 'TI', label: 'Tarjeta de Identidad' },
];

interface PacienteReciente {
  usuario_id: string;
  nombres: string;
  apellidos: string;
  tipo_documento: string;
  numero_documento: string;
  fecha_acceso: string;
}

export default function MedicoHCEPage() {
  const { medicoId, setMedicoId } = useAuthStore();
  const [tipoDoc, setTipoDoc] = useState('CC');
  const [numeroDoc, setNumeroDoc] = useState('');
  const [busqueda, setBusqueda] = useState<PacienteReciente | null>(null);

  useEffect(() => {
    if (!medicoId) {
      authApi.getMedicoId().then((res) => {
        setMedicoId(res.data.medico_id);
      }).catch(() => {});
    }
  }, [medicoId, setMedicoId]);

  const { data: citas = [], isLoading: loadingCitas } = useQuery<any[]>({
    queryKey: ['citas-medico-hce', medicoId],
    queryFn: async () => {
      if (!medicoId) return [];
      const res = await citasApi.getCitasMedico(medicoId);
      return res.data;
    },
    enabled: !!medicoId,
  } as any);

  const usuarioIds = [...new Set(citas.map((c: any) => c.usuario_id).filter(Boolean))];

  const { data: pacientesMap = {}, isLoading: loadingPacientes } = useQuery<Record<string, any>>({
    queryKey: ['pacientes-hce', usuarioIds],
    queryFn: async () => {
      const results: Record<string, any> = {};
      await Promise.all(
        usuarioIds.map(async (uid: string) => {
          try {
            const res = await userApi.getById(uid);
            results[uid] = res.data;
          } catch {
            results[uid] = { nombres: 'Paciente', apellidos: uid.slice(0, 8), tipo_documento: 'CC', numero_documento: '—' };
          }
        })
      );
      return results;
    },
    enabled: usuarioIds.length > 0,
  } as any);

  const recientes: PacienteReciente[] = usuarioIds.map((uid: string) => {
    const u = pacientesMap[uid];
    const citaMax = citas.filter((c: any) => c.usuario_id === uid).sort((a: any, b: any) => b.fecha_cita.localeCompare(a.fecha_cita))[0];
    return {
      usuario_id: uid,
      nombres: u?.nombres ?? 'Paciente',
      apellidos: u?.apellidos ?? uid.slice(0, 8),
      tipo_documento: u?.tipo_documento ?? 'CC',
      numero_documento: u?.numero_documento ?? '—',
      fecha_acceso: citaMax?.fecha_cita ?? new Date().toISOString(),
    };
  });

  const handleBuscar = async () => {
    if (!numeroDoc.trim()) return;
    try {
      const res = await userApi.buscarPorDocumento(tipoDoc, numeroDoc.trim());
      const u = res.data;
      setBusqueda({
        usuario_id: u.usuario_id,
        nombres: u.nombres,
        apellidos: u.apellidos,
        tipo_documento: u.tipo_documento,
        numero_documento: u.numero_documento,
        fecha_acceso: new Date().toISOString(),
      });
    } catch {
      setBusqueda(null);
    }
  };

  const loading = loadingCitas || loadingPacientes;
  const listaPacientes = busqueda ? [busqueda] : recientes;

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-[#2B3E59]">Historias Clínicas</h1>
        <p className="text-gray-500 text-sm mt-1">Busca pacientes por número de documento</p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <select
            value={tipoDoc}
            onChange={(e) => setTipoDoc(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30 w-full sm:w-48"
          >
            {TIPO_DOC_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={numeroDoc}
            onChange={(e) => setNumeroDoc(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleBuscar()}
            placeholder="Número de documento"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
          />
          <button
            onClick={handleBuscar}
            className="bg-[#2B3E59] text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-[#1e2d40] transition-colors flex items-center gap-2"
          >
            <Search size={16} />
            Buscar
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={18} className="text-[#2B3E59]" />
          <h2 className="font-semibold text-gray-800">
            {busqueda ? 'Resultado de búsqueda' : 'Pacientes recientes'}
          </h2>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 size={24} className="animate-spin text-[#2B3E59]" />
          </div>
        ) : listaPacientes.length > 0 ? (
          <ul className="space-y-2">
            {listaPacientes.map((p) => (
              <li key={p.usuario_id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors">
                <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                  <User size={18} className="text-gray-500" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">{p.nombres} {p.apellidos}</p>
                  <p className="text-xs text-gray-500">{p.tipo_documento} {p.numero_documento}</p>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400 text-sm text-center py-8">
            {busqueda ? 'Paciente no encontrado' : 'Sin pacientes con citas registradas'}
          </p>
        )}
      </div>
    </div>
  );
}
