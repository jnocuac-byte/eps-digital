import { useState } from 'react';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';

const DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MESES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

export default function MedicoAgendaPage() {
  const [mesActual, setMesActual] = useState(new Date());
  const [diaSeleccionado, setDiaSeleccionado] = useState<Date | null>(null);

  const year = mesActual.getFullYear();
  const month = mesActual.getMonth();
  const primerDia = new Date(year, month, 1).getDay();
  const diasEnMes = new Date(year, month + 1, 0).getDate();
  const offset = (primerDia + 6) % 7;

  const dias: (number | null)[] = [];
  for (let i = 0; i < offset; i++) dias.push(null);
  for (let i = 1; i <= diasEnMes; i++) dias.push(i);

  const cambiarMes = (delta: number) => {
    const d = new Date(mesActual);
    d.setMonth(d.getMonth() + delta);
    setMesActual(d);
  };

  const hoy = new Date();
  const esHoy = (dia: number) =>
    dia === hoy.getDate() && month === hoy.getMonth() && year === hoy.getFullYear();

  const seleccionado = (dia: number) =>
    diaSeleccionado?.getDate() === dia &&
    diaSeleccionado?.getMonth() === month &&
    diaSeleccionado?.getFullYear() === year;

  return (
    <div className="max-w-[1440px] mx-auto px-4 sm:px-6 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-[#2B3E59]">Mi Agenda</h1>
          <p className="text-gray-500 text-sm mt-1">Gestiona tu disponibilidad y horarios</p>
        </div>
        <button className="bg-[#2B3E59] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1e2d40] transition-colors">
          Configurar disponibilidad
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-6">
          <button onClick={() => cambiarMes(-1)} className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50">
            <ChevronLeft size={18} />
          </button>
          <h2 className="text-lg font-semibold text-gray-800">
            {MESES[month]} {year}
          </h2>
          <button onClick={() => cambiarMes(1)} className="p-2 rounded-lg border border-gray-200 hover:bg-gray-50">
            <ChevronRight size={18} />
          </button>
        </div>

        <div className="grid grid-cols-7 gap-1">
          {DIAS.map((d) => (
            <div key={d} className="text-center text-xs font-medium text-gray-500 py-2">
              {d}
            </div>
          ))}
          {dias.map((dia, i) => (
            <div
              key={i}
              onClick={() => dia && setDiaSeleccionado(new Date(year, month, dia))}
              className={`aspect-square flex flex-col items-center justify-center rounded-lg text-sm cursor-pointer transition-colors ${
                dia === null
                  ? ''
                  : esHoy(dia)
                  ? 'bg-[#2B3E59] text-white font-semibold'
                  : seleccionado(dia)
                  ? 'bg-blue-100 text-[#2B3E59] font-semibold'
                  : 'hover:bg-gray-100 text-gray-700'
              }`}
            >
              {dia}
            </div>
          ))}
        </div>
      </div>

      {diaSeleccionado && (
        <div className="mt-6 bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={18} className="text-[#2B3E59]" />
            <h3 className="font-semibold text-gray-800">
              {diaSeleccionado.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
            </h3>
          </div>
          <p className="text-gray-500 text-sm">Sin citas programadas para este día</p>
        </div>
      )}
    </div>
  );
}
