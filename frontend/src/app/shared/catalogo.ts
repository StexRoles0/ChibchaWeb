import { ResumenDTO } from '../core/api/dto';
import { decimalACentavos, descuentoAPuntosBasicos } from './monto';

export interface Paquete {
  id: number;
  nombre: string;
  tarifaCentavos: number;
  /** "10.00", tal como llega */
  tarifa: string;
}

export interface Plan {
  id: number;
  nombre: string;
  meses: number;
  descuentoPuntosBasicos: number;
}

/** `GET /catalogo/paquetes`: subtitulo = "10.00". */
export function aPaquete(r: ResumenDTO): Paquete {
  return {
    id: r.id,
    nombre: r.titulo,
    tarifa: r.subtitulo,
    tarifaCentavos: decimalACentavos(r.subtitulo),
  };
}

/** `GET /catalogo/planes`: subtitulo = "3|0.05" (meses|descuento). */
export function aPlan(r: ResumenDTO): Plan {
  const [meses, descuento] = r.subtitulo.split('|');
  return {
    id: r.id,
    nombre: r.titulo,
    meses: Number(meses),
    descuentoPuntosBasicos: descuentoAPuntosBasicos(descuento ?? '0'),
  };
}

/** 1500 → "15" (porcentaje para mostrar); 750 → "7.5" */
export function porcentaje(puntosBasicos: number): string {
  return String(puntosBasicos / 100);
}
