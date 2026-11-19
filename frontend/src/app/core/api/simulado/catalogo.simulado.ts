import { ResumenDTO } from '../dto';
import { ManejadorSim } from './tipos';

/** Datos de `schema.sql` (tarifas de reglas-negocio.md). */
export const PAQUETES_SIM: ResumenDTO[] = [
  { id: 1, titulo: 'Chibcha-Plata', subtitulo: '5.00', estado: 'ACTIVO' },
  { id: 2, titulo: 'Chibcha-Oro', subtitulo: '10.00', estado: 'ACTIVO' },
  { id: 3, titulo: 'Chibcha-Platino', subtitulo: '20.00', estado: 'ACTIVO' },
];

/** subtitulo = "meses|descuento" */
export const PLANES_SIM: ResumenDTO[] = [
  { id: 1, titulo: 'Mensual', subtitulo: '1|0.00', estado: 'ACTIVO' },
  { id: 2, titulo: 'Trimestral', subtitulo: '3|0.05', estado: 'ACTIVO' },
  { id: 3, titulo: 'Semestral', subtitulo: '6|0.10', estado: 'ACTIVO' },
  { id: 4, titulo: 'Anual', subtitulo: '12|0.15', estado: 'ACTIVO' },
];

export const catalogoSimulado: ManejadorSim = (p) => {
  if (p.metodo !== 'GET') return undefined;
  if (p.ruta === '/catalogo/paquetes') return { estado: 200, cuerpo: PAQUETES_SIM };
  if (p.ruta === '/catalogo/planes') return { estado: 200, cuerpo: PLANES_SIM };
  return undefined;
};
