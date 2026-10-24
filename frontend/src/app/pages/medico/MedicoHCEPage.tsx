import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Clock, ChevronDown, Loader2, RotateCcw } from 'lucide-react';
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
  const mostrarRecientes = () => {
    setBusqueda(null);
    setNumeroDoc('');
  };

  return (
    <div className="medico-page-enter max-w-[1440px] mx-auto px-4 sm:px-6 py-8 lg:py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-[#2B3E59]">Historias Clínicas</h1>
        <p className="text-gray-500 text-sm mt-1">Busca pacientes por número de documento</p>
      </div>

      <div className="space-y-4">
        <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm md:p-6">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e7f0ef] text-[#2B3E59]">
              <Search size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#2B3E59]">Buscar historia clínica</p>
              <p className="text-xs text-gray-500">Ingresa el documento del paciente</p>
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative w-full sm:w-56">
              <select
                value={tipoDoc}
                onChange={(e) => setTipoDoc(e.target.value)}
                className="w-full appearance-none rounded-xl border border-gray-300 bg-[#f7faf9] px-3 py-3 pr-10 text-sm font-medium text-[#2B3E59] outline-none transition-colors hover:border-[#466b79] focus:border-[#466b79] focus:ring-2 focus:ring-[#466b79]/30"
              >
                {TIPO_DOC_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <ChevronDown size={16} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[#466b79]" />
            </div>
            <input
              type="text"
              value={numeroDoc}
              onChange={(e) => setNumeroDoc(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleBuscar()}
              placeholder="Número de documento"
              className="flex-1 rounded-xl border border-gray-300 px-3 py-3 text-sm outline-none transition-colors focus:border-[#466b79] focus:ring-2 focus:ring-[#466b79]/30"
            />
            <button
              onClick={handleBuscar}
              className="flex items-center gap-2 rounded-xl bg-[#2B3E59] px-6 py-3 text-sm font-medium text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-[#1e2d40]"
            >
              <Search size={16} />
              Buscar
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm md:p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e7f0ef] text-[#2B3E59]">
                <Clock size={18} />
              </div>
              <div>
                <h2 className="text-base font-semibold text-[#2B3E59]">
                  {busqueda ? 'Resultado de búsqueda' : 'Pacientes recientes'}
                </h2>
                {!busqueda && (
                  <p className="mt-0.5 text-xs text-gray-500">Accede rápidamente a tus últimos pacientes</p>
                )}
              </div>
            </div>
            {!busqueda && recientes.length > 0 && (
              <span className="rounded-full bg-[#edf3f3] px-2.5 py-1 text-xs font-semibold text-[#2B3E59]">
                {recientes.length}
              </span>
            )}
            {busqueda && (
              <button
                onClick={mostrarRecientes}
                className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-[#2B3E59] transition-colors hover:bg-[#edf3f3]"
              >
                <RotateCcw size={14} />
                Ver pacientes recientes
              </button>
            )}
          </div>
        {loading ? (
          <div className="flex items-center justify-center py-10">
            <Loader2 size={24} className="animate-spin text-[#2B3E59]" />
          </div>
        ) : listaPacientes.length > 0 ? (
          <ul className="divide-y divide-gray-100 overflow-hidden rounded-2xl border border-gray-100">
            {listaPacientes.map((p) => (
              <li key={p.usuario_id} className="group flex cursor-pointer items-center gap-3 p-4 transition-[background-color,box-shadow,transform] duration-200 hover:bg-[#f5f9f8] hover:shadow-sm">
                <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl bg-[#dcebea] text-sm font-bold text-[#2B3E59] transition-transform duration-200 group-hover:scale-105">
                  {`${p.nombres.charAt(0)}${p.apellidos.charAt(0)}`.toUpperCase()}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[#223044]">{p.nombres} {p.apellidos}</p>
                  <p className="mt-0.5 text-xs font-medium text-gray-500">{p.tipo_documento} · {p.numero_documento}</p>
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
    </div>
  );
}
