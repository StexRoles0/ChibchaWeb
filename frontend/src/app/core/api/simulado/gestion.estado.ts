import { ResumenDTO } from '../dto';
import { guardar, leer } from './almacen';
import { clientes, CODIGO_DISTRIBUIDOR_SIM, DISTRIBUIDOR_SIM } from './estado';

/** Empleado del modo simulado (tabla `usuario` + `empleado` de schema.sql). */
export interface EmpleadoSim {
  id: number;
  nombre: string;
  documento: string;
  correo: string;
  telefono: string;
  idRol: number;
  activo: boolean;
  fechaRegistro: string;
}

/** Distribuidor del modo simulado. `referidosBase` se suma a los clientes simulados que lo citan. */
export interface DistribuidorSim {
  id: number;
  nombre: string;
  documento: string;
  correo: string;
  telefono: string;
  codigo: string;
  referidosBase: number;
  activo: boolean;
}

/** `GET /catalogo/roles`: Roles de empleado (reglas-negocio.md). */
export const ROLES_SIM: ResumenDTO[] = [
  { id: 1, titulo: 'Gestión', subtitulo: '', estado: 'ACTIVO' },
  { id: 2, titulo: 'Soporte', subtitulo: '', estado: 'ACTIVO' },
  { id: 3, titulo: 'Administrador', subtitulo: '', estado: 'ACTIVO' },
];

/** Los tres empleados de `seed_dev.sql` más dos de demostración (uno dado de baja). */
const EMPLEADOS_INICIALES: EmpleadoSim[] = [
  {
    id: 1,
    nombre: 'Gabriela Gestión',
    documento: 'E-1001',
    correo: 'gestion@chibchaweb.co',
    telefono: '3001112233',
    idRol: 1,
    activo: true,
    fechaRegistro: '2026-01-12',
  },
  {
    id: 2,
    nombre: 'Sergio Soporte',
    documento: 'E-1002',
    correo: 'soporte@chibchaweb.co',
    telefono: '3002223344',
    idRol: 2,
    activo: true,
    fechaRegistro: '2026-01-12',
  },
  {
    id: 3,
    nombre: 'Ana Administra',
    documento: 'E-1003',
    correo: 'admin@chibchaweb.co',
    telefono: '3003334455',
    idRol: 3,
    activo: true,
    fechaRegistro: '2026-01-12',
  },
  {
    id: 4,
    nombre: 'Jorge Suárez Ramírez',
    documento: '1000000007',
    correo: 'jorge.suarez@chibchaweb.com',
    telefono: '311 222 3344',
    idRol: 2,
    activo: true,
    fechaRegistro: '2026-03-02',
  },
  {
    id: 5,
    nombre: 'Sara Díaz',
    documento: '1000000003',
    correo: 'sara.diaz@chibchaweb.com',
    telefono: '3105558899',
    idRol: 2,
    activo: false,
    fechaRegistro: '2026-02-20',
  },
];

/** El distribuidor de `seed_dev.sql` más tres de demostración (uno dado de baja). */
const DISTRIBUIDORES_INICIALES: DistribuidorSim[] = [
  {
    id: 10,
    nombre: DISTRIBUIDOR_SIM,
    documento: '900123456',
    correo: 'contacto@andesdigital.co',
    telefono: '6015556677',
    codigo: CODIGO_DISTRIBUIDOR_SIM,
    referidosBase: 128,
    activo: true,
  },
  {
    id: 11,
    nombre: 'Carlos Mesa',
    documento: '79456123',
    correo: 'carlos.mesa@correo.com',
    telefono: '3124445566',
    codigo: 'DIS-CME017',
    referidosBase: 64,
    activo: true,
  },
  {
    id: 12,
    nombre: 'Boyacá Web',
    documento: '901654321',
    correo: 'hola@boyacaweb.co',
    telefono: '6087771122',
    codigo: 'DIS-BOY031',
    referidosBase: 23,
    activo: true,
  },
  {
    id: 13,
    nombre: 'Lucía Torres',
    documento: '52987654',
    correo: 'lucia.torres@correo.com',
    telefono: '3157778899',
    codigo: 'DIS-LTO008',
    referidosBase: 0,
    activo: false,
  },
];

export const empleados = (): EmpleadoSim[] => leer('empleados', EMPLEADOS_INICIALES);
export const guardarEmpleados = (l: EmpleadoSim[]): void => guardar('empleados', l);

export const distribuidores = (): DistribuidorSim[] =>
  leer('distribuidores', DISTRIBUIDORES_INICIALES);
export const guardarDistribuidores = (l: DistribuidorSim[]): void => guardar('distribuidores', l);

/** Referidos = los de base más los clientes simulados cuyo distribuidor cita el código. */
export function referidosDe(d: DistribuidorSim): number {
  return (
    d.referidosBase +
    Object.values(clientes()).filter((c) => c.distribuidor.includes(`(${d.codigo})`)).length
  );
}

/** RN-19: Básica si tiene 100 referidos o menos, Premium desde 101. */
export const categoriaDe = (d: DistribuidorSim): string =>
  referidosDe(d) >= 101 ? 'Premium' : 'Básica';

/** RN-13: el código del registro debe ser de un distribuidor activo. */
export function distribuidorActivoPorCodigo(codigo: string): DistribuidorSim | undefined {
  return distribuidores().find((d) => d.activo && d.codigo === codigo.trim().toUpperCase());
}

/** RN-15: `DIS-` + 6 caracteres alfanuméricos en mayúscula, único. */
export function generarCodigoDistribuidor(): string {
  const ALFABETO = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789';
  const usados = new Set(distribuidores().map((d) => d.codigo));
  for (;;) {
    let c = 'DIS-';
    for (let i = 0; i < 6; i++) c += ALFABETO[Math.floor(Math.random() * ALFABETO.length)];
    if (!usados.has(c)) return c;
  }
}

export function hoyIso(): string {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, '0')}-${String(h.getDate()).padStart(2, '0')}`;
}
