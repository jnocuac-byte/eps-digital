import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  Calendar, TrendingUp, XCircle, AlertTriangle, Loader2, RefreshCw, Shield, Users,
} from 'lucide-react';
import { Link } from 'react-router';
import { citasApi } from '../../lib/apiClient';
import { useAuthStore } from '../../stores/authStore';
import type { MetricasCitas } from '../../types';

const PRIMARY = '#2B3E59';

// Tarjeta de métrica individual
function MetricCard({
  label, value, icon, color = PRIMARY,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex items-center gap-4">
      <div className="rounded-xl p-3" style={{ backgroundColor: `${color}15` }}>
        <div style={{ color }}>{icon}</div>
      </div>
      <div>
        <p className="text-gray-500 text-sm">{label}</p>
        <p className="text-2xl font-semibold text-gray-800">{value}</p>
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const { esSuperAdmin } = useAuthStore();
  const { data, isLoading, isError, refetch } = useQuery<MetricasCitas>({
    queryKey: ['metricas-citas'],
    queryFn: async () => {
      const res = await citasApi.getMetricas(7);
      return res.data;
    },
    onError: () => toast.error('No se pudieron cargar las métricas'),
  } as Parameters<typeof useQuery>[0]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 size={36} className="animate-spin text-[#2B3E59]" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle size={40} className="text-red-400" />
        <p className="text-gray-600">No se pudieron cargar las métricas</p>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 bg-[#2B3E59] text-white px-4 py-2 rounded-lg text-sm hover:opacity-90"
        >
          <RefreshCw size={16} /> Reintentar
        </button>
      </div>
    );
  }

  // Formatear fechas del gráfico para mostrar solo MM/DD
  const chartData = (data.por_dia ?? []).map((d) => ({
    fecha: d.fecha.slice(5), // MM-DD
    total: d.total,
  }));

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      {/* Cabecera */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Dashboard Administrativo</h1>
          <p className="text-gray-500 text-sm mt-1">Últimos 7 días · Actualizado en tiempo real</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 text-sm text-[#2B3E59] border border-[#2B3E59] rounded-lg px-4 py-2 hover:bg-[#2B3E59] hover:text-white transition-colors"
        >
          <RefreshCw size={15} /> Actualizar
        </button>
      </div>

      {/* Tarjetas de métricas */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        <MetricCard label="Citas hoy" value={data.total_hoy} icon={<Calendar size={22} />} />
        <MetricCard
          label="Citas esta semana"
          value={data.total_semana}
          icon={<TrendingUp size={22} />}
          color="#10b981"
        />
        <MetricCard
          label="Tasa de cancelación"
          value={`${data.tasa_cancelacion?.toFixed(1) ?? 0}%`}
          icon={<XCircle size={22} />}
          color="#f59e0b"
        />
        <MetricCard
          label="Canceladas"
          value={data.canceladas}
          icon={<AlertTriangle size={22} />}
          color="#ef4444"
        />
      </div>

      {/* Gráfico de barras */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
        <h2 className="text-base font-semibold text-[#2B3E59] mb-4">Citas por día (últimos 7 días)</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="fecha" tick={{ fontSize: 12, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                formatter={(v: number) => [v, 'Citas']}
              />
              <Bar dataKey="total" fill={PRIMARY} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-gray-400 text-sm text-center py-10">Sin datos disponibles</p>
        )}
      </div>

      {/* Top especialidades y top médicos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top especialidades */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-[#2B3E59] mb-4">Top 5 Especialidades</h2>
          {(data.top_especialidades ?? []).slice(0, 5).length > 0 ? (
            <ul className="space-y-3">
              {data.top_especialidades.slice(0, 5).map((esp, i) => (
                <li key={esp.nombre} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-[#2B3E59]/10 text-[#2B3E59] flex items-center justify-center text-xs font-semibold">
                      {i + 1}
                    </span>
                    <span className="text-sm text-gray-700">{esp.nombre}</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-800">{esp.total} citas</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 text-sm">Sin datos</p>
          )}
        </div>

        {/* Top médicos */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-base font-semibold text-[#2B3E59] mb-4">Top 5 Médicos</h2>
          {(data.top_medicos ?? []).slice(0, 5).length > 0 ? (
            <ul className="space-y-3">
              {data.top_medicos.slice(0, 5).map((med, i) => (
                <li key={med.medico_id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 rounded-full bg-[#2B3E59]/10 text-[#2B3E59] flex items-center justify-center text-xs font-semibold">
                      {i + 1}
                    </span>
                    <span className="text-sm text-gray-700">{med.nombres}</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-800">{med.total} citas</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-400 text-sm">Sin datos</p>
          )}
        </div>
      </div>

      {/* Accesos rapidos */}
      {esSuperAdmin && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mt-6">
          <h2 className="text-base font-semibold text-[#2B3E59] mb-4">Accesos Rápidos</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Link
              to="/admin/medicos"
              className="flex items-center gap-3 p-4 rounded-xl border border-gray-100 hover:border-[#2B3E59] hover:bg-[#2B3E59]/5 transition-colors"
            >
              <Users size={24} className="text-[#2B3E59]" />
              <div>
                <p className="text-sm font-medium text-gray-800">Médicos</p>
                <p className="text-xs text-gray-500">Gestionar médicos</p>
              </div>
            </Link>
            <Link
              to="/admin/admins"
              className="flex items-center gap-3 p-4 rounded-xl border border-gray-100 hover:border-[#2B3E59] hover:bg-[#2B3E59]/5 transition-colors"
            >
              <Shield size={24} className="text-[#2B3E59]" />
              <div>
                <p className="text-sm font-medium text-gray-800">Administradores</p>
                <p className="text-xs text-gray-500">Gestionar admins</p>
              </div>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
