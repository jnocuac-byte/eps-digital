// Helpers de fechas: evitan el desfase UTC al parsear o formatear fechas de calendario.
// new Date("YYYY-MM-DD") se interpreta como medianoche UTC y en Colombia (UTC-5)
// muestra el dia anterior; estos helpers fijan la hora LOCAL.

// Convierte una fecha ("YYYY-MM-DD" o ISO completo) a Date local sin desfase UTC.
export function parseFechaLocal(valor: string): Date {
  return new Date(`${valor.slice(0, 10)}T00:00:00`);
}

// Formatea una Date a "YYYY-MM-DD" en hora LOCAL (sin desfase UTC).
export function toISODateLocal(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
