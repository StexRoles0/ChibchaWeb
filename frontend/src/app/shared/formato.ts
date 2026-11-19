import { DetalleDTO } from '../core/api/dto';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** "2027-09-14" → "14 sep 2027" */
export function fechaCorta(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${Number(m[3])} ${MESES[Number(m[2]) - 1] ?? m[2]} ${m[1]}`;
}

/** "2028-08-01" → "08/28" */
export function vencimientoCorto(iso: string): string {
  const m = /^(\d{4})-(\d{2})-\d{2}/.exec(iso);
  return m ? `${m[2]}/${m[1].slice(2)}` : iso;
}

/** `DetalleDTO.campos` ("clave: valor") → objeto. Una clave repetida conserva la última. */
export function camposDeDetalle(detalle: DetalleDTO): Record<string, string> {
  const salida: Record<string, string> = {};
  for (const campo of detalle.campos) {
    const i = campo.indexOf(':');
    if (i < 0) continue;
    salida[campo.slice(0, i).trim()] = campo.slice(i + 1).trim();
  }
  return salida;
}

export const primerNombre = (nombre: string): string => nombre.trim().split(/\s+/)[0] ?? '';

const dos = (n: number): string => String(n).padStart(2, '0');

/** Fecha local de hoy en `AAAA-MM-DD`. */
export function hoyIso(ahora = new Date()): string {
  return `${ahora.getFullYear()}-${dos(ahora.getMonth() + 1)}-${dos(ahora.getDate())}`;
}

/** "2026-09-14" → "14/09/2026" */
export function fechaDMA(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}

/** "2026-11-01" → "domingo 1 de noviembre de 2026" */
export function fechaLarga(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!m) return iso;
  const f = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), 12);
  return new Intl.DateTimeFormat('es-CO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
    .format(f)
    .replace(',', '');
}

/** Instante ISO → "Hoy, 09:14" o "14 sep 2026, 09:14" (hora local). */
export function fechaHoraCorta(iso: string, ahora = new Date()): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const hora = `${dos(d.getHours())}:${dos(d.getMinutes())}`;
  const dia = hoyIso(d);
  return dia === hoyIso(ahora) ? `Hoy, ${hora}` : `${fechaCorta(dia)}, ${hora}`;
}
