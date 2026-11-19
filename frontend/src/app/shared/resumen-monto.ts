import { Paquete, Plan, porcentaje } from './catalogo';
import { calcularMonto, centavosADecimal } from './monto';

export interface DesgloseTexto {
  paquete: string;
  plan: string;
  meses: number;
  descuentoPct: string;
  bruto: string;
  descuento: string;
  total: string;
}

/** Vista previa RN-01 lista para mostrar (montos como string decimal). */
export function aMontoTexto(paquete: Paquete, plan: Plan): DesgloseTexto {
  const d = calcularMonto(paquete.tarifaCentavos, plan.meses, plan.descuentoPuntosBasicos);
  return {
    paquete: paquete.nombre,
    plan: plan.nombre.toLowerCase(),
    meses: plan.meses,
    descuentoPct: porcentaje(plan.descuentoPuntosBasicos),
    bruto: centavosADecimal(d.brutoCentavos),
    descuento: centavosADecimal(d.descuentoCentavos),
    total: centavosADecimal(d.totalCentavos),
  };
}
