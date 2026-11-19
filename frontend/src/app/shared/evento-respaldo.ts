const AGREGADOS: Record<string, string> = {
  Usuario: 'Usuario',
  Suscripcion: 'Suscripción',
  Comision: 'Comisión',
  SolicitudDominio: 'Solicitud de dominio',
};

const OPERACIONES: Record<string, string> = {
  insertar: 'creación',
  actualizar: 'modificación',
  registrar_pago: 'registro de pago',
  registrar_cheque: 'registro de cheque',
};

/**
 * Tipo técnico de un evento respaldado (`Suscripcion.registrar_pago`) → texto legible
 * ("Suscripción · registro de pago"). Lo que no se reconoce se muestra tal cual.
 */
export function etiquetaEvento(tipo: string): string {
  const [agregado, operacion, ...resto] = tipo.split('.');
  const a = AGREGADOS[agregado];
  const o = OPERACIONES[operacion ?? ''];
  if (!a || !o || resto.length > 0) return tipo;
  return `${a} · ${o}`;
}
