/** Categorías de ticket: el contrato usa el literal del enum; la interfaz muestra la etiqueta. */
export const CATEGORIAS_TICKET: { valor: string; etiqueta: string }[] = [
  { valor: 'RENDIMIENTO', etiqueta: 'Rendimiento' },
  { valor: 'CORREO', etiqueta: 'Correo' },
  { valor: 'BASE_DATOS', etiqueta: 'Base de datos' },
  { valor: 'DOMINIO', etiqueta: 'Dominio' },
  { valor: 'OTRA', etiqueta: 'Otra' },
];

/** `BASE_DATOS` → "Base de datos". Un literal desconocido se muestra legible. */
export function etiquetaCategoria(literal: string): string {
  const c = CATEGORIAS_TICKET.find((x) => x.valor === literal.trim().toUpperCase());
  if (c) return c.etiqueta;
  const t = literal.replace(/_/g, ' ').toLowerCase();
  return t.charAt(0).toUpperCase() + t.slice(1);
}
