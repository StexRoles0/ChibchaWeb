import { Pipe, PipeTransform } from '@angular/core';

/** "20.00" → 2000. Aritmética en centavos: nunca se usa float para el dinero. */
export function decimalACentavos(valor: string): number {
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(valor.trim());
  if (!m) return Number.NaN;
  return Number(m[1]) * 100 + Number((m[2] ?? '').padEnd(2, '0'));
}

/** 5400 → "54.00" */
export function centavosADecimal(centavos: number): string {
  const entero = Math.floor(centavos / 100);
  const resto = centavos % 100;
  return `${entero}.${String(resto).padStart(2, '0')}`;
}

/** Descuento como string decimal ("0.15") → puntos básicos (1500), sin float. */
export function descuentoAPuntosBasicos(valor: string): number {
  const m = /^(\d+)(?:\.(\d{1,4}))?$/.exec(valor.trim());
  if (!m) return Number.NaN;
  return Number(m[1]) * 10000 + Number((m[2] ?? '').padEnd(4, '0'));
}

export interface DesgloseMonto {
  /** tarifa × meses, sin descuento */
  brutoCentavos: number;
  /** lo que se descuenta */
  descuentoCentavos: number;
  /** monto del periodo (RN-01) */
  totalCentavos: number;
}

/**
 * RN-01: monto = tarifaMensual × meses × (1 − descuento), a 2 decimales con ROUND_HALF_UP.
 * Solo es vista previa: el backend vuelve a calcular.
 */
export function calcularMonto(
  tarifaCentavos: number,
  meses: number,
  descuentoPuntosBasicos: number,
): DesgloseMonto {
  const brutoCentavos = tarifaCentavos * meses;
  const numerador = brutoCentavos * (10000 - descuentoPuntosBasicos);
  const totalCentavos = Math.floor((numerador + 5000) / 10000);
  return { brutoCentavos, descuentoCentavos: brutoCentavos - totalCentavos, totalCentavos };
}

/** Pipe `monto`: "54.00" → "US$ 54.00". */
@Pipe({ name: 'monto' })
export class MontoPipe implements PipeTransform {
  transform(valor: string | null | undefined): string {
    if (valor === null || valor === undefined || valor === '') return '';
    return `US$ ${valor}`;
  }
}
