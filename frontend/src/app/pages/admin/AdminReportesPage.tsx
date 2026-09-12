import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Download, Search, Loader2, FileText, AlertTriangle } from 'lucide-react';
import { citasApi } from '../../lib/apiClient';
import { toISODateLocal } from '../../lib/fechas';
import type { Cita } from '../../types';

// Utilidad para exportar un array de objetos como CSV
function exportarCSV(data: Record<string, unknown>[], nombreArchivo: string) {
  if (!data.length) {
    toast.warning('No hay datos para exportar');
    return;
  }
  const headers = Object.keys(data[0]).join(',');
  const filas = data.map((fila) =>
    Object.values(fila)
      .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`)
      .join(','),
  );
  const csv = [headers, ...filas].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = nombreArchivo;
  link.click();
  URL.revokeObjectURL(url);
  toast.success(`Exportado: ${nombreArchivo}`);
}

// Etiqueta de estado con color
const estadoColor: Record<string, string> = {
  programada: 'bg-blue-50 text-blue-700',
  cancelada: 'bg-red-50 text-red-700',
  atendida: 'bg-green-50 text-green-700',
  no_asistio: 'bg-yellow-50 text-yellow-700',
};

export default function AdminReportesPage() {
  const hoy = toISODateLocal(new Date());
  const haceUnMes = toISODateLocal(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));

  const [fechaInicio, setFechaInicio] = useState(haceUnMes);
  const [fechaFin, setFechaFin] = useState(hoy);
  const [buscar, setBuscar] = useState(false);

  // Consulta citas canceladas en el rango seleccionado
  const { data: citas = [], isLoading, isError } = useQuery<Cita[]>({
    queryKey: ['reporte-canceladas', fechaInicio, fechaFin, buscar],
    queryFn: async () => {
      const res = await citasApi.getCanceladas({ fecha_inicio: fechaInicio, fecha_fin: fechaFin });
      return res.data;
    },
    enabled: buscar,
    onError: () => toast.error('Error al cargar el reporte'),
  } as Parameters<typeof useQuery>[0]);

  const handleBuscar = (e: React.FormEvent) => {
    e.preventDefault();
    setBuscar(true);
  };

  const handleExportar = () => {
    const filas = citas.map((c) => ({
      cita_id: c.cita_id,
      usuario_id: c.usuario_id,
      medico: c.medico_nombre ?? '',
      especialidad: c.especialidad_nombre ?? '',
      fecha_cita: c.fecha_cita,
      hora_inicio: c.hora_inicio,
      estado: c.estado,
      sede: c.sede_nombre ?? '',
    }));
    exportarCSV(filas as unknown as Record<string, unknown>[], `reporte_canceladas_${fechaInicio}_${fechaFin}.csv`);
  };

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      {/* Cabecera */}
      <div className="flex items-center gap-3 mb-8">
        <div className="p-3 rounded-xl bg-[#2B3E59]/10">
          <FileText size={22} className="text-[#2B3E59]" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Reportes</h1>
          <p className="text-gray-500 text-sm">Exporta información de citas por rango de fechas</p>
        </div>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
        <h2 className="text-base font-semibold text-gray-800 mb-4">Citas canceladas por período</h2>
        <form onSubmit={handleBuscar} className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Fecha inicio</label>
            <input
              type="date"
              value={fechaInicio}
              onChange={(e) => { setFechaInicio(e.target.value); setBuscar(false); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Fecha fin</label>
            <input
              type="date"
              value={fechaFin}
              onChange={(e) => { setFechaFin(e.target.value); setBuscar(false); }}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#2B3E59]/30"
            />
          </div>
          <button
            type="submit"
            className="flex items-center gap-2 bg-[#2B3E59] text-white px-5 py-2 rounded-lg text-sm hover:opacity-90"
          >
            <Search size={15} /> Consultar
          </button>
          {citas.length > 0 && (
            <button
              type="button"
              onClick={handleExportar}
              className="flex items-center gap-2 border border-[#2B3E59] text-[#2B3E59] px-5 py-2 rounded-lg text-sm hover:bg-[#2B3E59] hover:text-white transition-colors"
            >
              <Download size={15} /> Exportar CSV
            </button>
          )}
        </form>
      </div>

      {/* Resultados */}
      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={32} className="animate-spin text-[#2B3E59]" />
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-100 rounded-xl p-4 text-red-700 text-sm">
          <AlertTriangle size={18} />
          No se pudo cargar el reporte. Verifica el rango de fechas.
        </div>
      )}

      {!isLoading && buscar && !isError && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <p className="text-sm font-medium text-gray-700">
              {citas.length} citas canceladas en el período
            </p>
            {citas.length > 0 && (
              <button
                onClick={handleExportar}
                className="flex items-center gap-1.5 text-sm text-[#2B3E59] hover:underline"
              >
                <Download size={14} /> Descargar CSV
              </button>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-50">
                  <th className="px-5 py-3 text-gray-500 font-medium">Fecha</th>
                  <th className="px-5 py-3 text-gray-500 font-medium">Hora</th>
                  <th className="px-5 py-3 text-gray-500 font-medium">Especialidad</th>
                  <th className="px-5 py-3 text-gray-500 font-medium">Médico</th>
                  <th className="px-5 py-3 text-gray-500 font-medium">Sede</th>
                  <th className="px-5 py-3 text-gray-500 font-medium">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {citas.map((c) => (
                  <tr key={c.cita_id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 text-gray-700">{c.fecha_cita}</td>
                    <td className="px-5 py-3 text-gray-600">{c.hora_inicio}</td>
                    <td className="px-5 py-3 text-gray-700">{c.especialidad_nombre ?? '—'}</td>
                    <td className="px-5 py-3 text-gray-700">{c.medico_nombre ?? '—'}</td>
                    <td className="px-5 py-3 text-gray-600">{c.sede_nombre ?? '—'}</td>
                    <td className="px-5 py-3">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${estadoColor[c.estado] ?? ''}`}>
                        {c.estado.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))}
                {citas.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-gray-400">
                      No hay citas canceladas en el período seleccionado
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!buscar && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <FileText size={40} className="opacity-30" />
          <p className="text-sm">Selecciona un período y haz clic en "Consultar"</p>
        </div>
      )}
    </div>
  );
}
