import { DetalleDTO } from '../../core/api/dto';

/** Niveles de servicio (reglas-negocio.md): Soporte (1) → Gestión (2) → Desarrollo (3, último). */
export const NIVELES = ['Soporte', 'Gestión', 'Desarrollo'];

export interface Movimiento {
  fecha: string;
  responsable: string;
  estado: string;
  nivel: string;
  observacion: string;
}

export interface Ticket {
  id: number;
  categoria: string;
  estado: string;
  nivel: string;
  reportante: string;
  sitio: string;
  fechaCreacion: string;
  descripcion: string;
  movimientos: Movimiento[];
}

/** Nombre del nivel siguiente, o `null` si ya es el último (o no se reconoce). */
export function nivelSiguiente(nivel: string): string | null {
  const i = NIVELES.indexOf(nivel);
  return i >= 0 && i < NIVELES.length - 1 ? NIVELES[i + 1] : null;
}

/**
 * `DetalleDTO` de un ticket → objeto. `movimiento` se repite:
 * `"2026-11-16 10:30|Ana Ruiz|ESCALADO|Gestión|observación"`.
 */
export function aTicket(d: DetalleDTO): Ticket {
  const simples: Record<string, string> = {};
  const movimientos: Movimiento[] = [];
  for (const campo of d.campos) {
    const i = campo.indexOf(':');
    if (i < 0) continue;
    const clave = campo.slice(0, i).trim();
    const valor = campo.slice(i + 1).trim();
    if (clave === 'movimiento') {
      const [fecha = '', responsable = '', estado = '', nivel = '', ...resto] = valor.split('|');
      movimientos.push({ fecha, responsable, estado, nivel, observacion: resto.join('|') });
    } else {
      simples[clave] = valor;
    }
  }
  return {
    id: d.id,
    categoria: simples['categoria'] ?? '',
    estado: (simples['estado'] ?? '').toUpperCase(),
    nivel: simples['nivel'] ?? '',
    reportante: simples['reportante'] ?? '',
    sitio: simples['sitio'] ?? '',
    fechaCreacion: simples['fechaCreacion'] ?? '',
    descripcion: simples['descripcion'] ?? '',
    movimientos,
  };
}
