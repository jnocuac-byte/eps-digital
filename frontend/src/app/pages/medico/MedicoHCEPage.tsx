import { useState } from 'react';
import { Search, Clock, User } from 'lucide-react';

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

const PACIENTES_MOCK: PacienteReciente[] = [
  { usuario_id: '1', nombres: 'María', apellidos: 'García', tipo_documento: 'CC', numero_documento: '1234567890', fecha_acceso: new Date().toISOString() },
  { usuario_id: '2', nombres: 'Carlos', apellidos: 'Rodríguez', tipo_documento: 'CC', numero_documento: '9876543210', fecha_acceso: new Date(Date.now() - 86400000).toISOString() },
];

export default function MedicoHCEPage() {
  const [tipoDoc, setTipoDoc] = useState('CC');
  const [numeroDoc, setNumeroDoc] = useState('');
  const [recientes] = useState<PacienteReciente[]>(PACIENTES_MOCK);

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
            placeholder="Número de documento"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
          />
          <button className="bg-[#2B3E59] text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-[#1e2d40] transition-colors flex items-center gap-2">
            <Search size={16} />
            Buscar
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={18} className="text-[#2B3E59]" />
          <h2 className="font-semibold text-gray-800">Pacientes recientes</h2>
        </div>
        {recientes.length > 0 ? (
          <ul className="space-y-2">
            {recientes.map((p) => (
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
          <p className="text-gray-400 text-sm text-center py-8">Sin pacientes recientes</p>
        )}
      </div>
    </div>
  );
}
