import { DatosClienteDTO, ResultadoAccesoDTO } from '../dto';
import { guardar, leer } from './almacen';
import { fijarUsuarioSimulado, USUARIOS_SIMULADOS, usuarioSimuladoActual } from './sesiones';

/** Cliente del modo simulado (lo que el backend tendría en la BD). */
export interface ClienteSim {
  idUsuario: number;
  nombre: string;
  correo: string;
  activo: boolean;
  telefono: string;
  lineaResidencia: string;
  ciudadResidencia: string;
  codigoPostalResidencia: string;
  lineaFacturacion: string;
  ciudadFacturacion: string;
  codigoPostalFacturacion: string;
  /** Solo los últimos 4 dígitos: el número completo nunca se guarda. */
  ultimos4: string;
  franquicia: DatosClienteDTO['franquicia'];
  vencimiento: string;
  idSuscripcion: number;
  /** Nombre corto; el subdominio es `<sitio>.chibchaweb.com` (RN-14). */
  sitio: string;
  plataforma: 'WINDOWS' | 'UNIX';
  idPaquete: number;
  idPlan: number;
  fechaCorte: string;
  distribuidor: string;
}

export const DOMINIO_BASE = 'chibchaweb.com';
export const CODIGO_DISTRIBUIDOR_SIM = 'DIS-ANDES1';
export const DISTRIBUIDOR_SIM = 'Andes Digital SAS';

const STEVEN: ClienteSim = {
  idUsuario: 1,
  nombre: 'Steven Navarro Parrales',
  correo: 'steven@correo.co',
  activo: true,
  telefono: '300 412 5587',
  lineaResidencia: 'Calle 24 # 7-31',
  ciudadResidencia: 'Sogamoso',
  codigoPostalResidencia: '152210',
  lineaFacturacion: 'Calle 24 # 7-31',
  ciudadFacturacion: 'Sogamoso',
  codigoPostalFacturacion: '152210',
  ultimos4: '1111',
  franquicia: 'VISA',
  vencimiento: '2028-08-01',
  idSuscripcion: 1,
  sitio: 'cafedeboyaca',
  plataforma: 'UNIX',
  idPaquete: 3,
  idPlan: 4,
  fechaCorte: '2027-09-14',
  distribuidor: '',
};

export function clientes(): Record<string, ClienteSim> {
  return { [STEVEN.correo]: STEVEN, ...leer<Record<string, ClienteSim>>('clientes', {}) };
}

export function guardarCliente(c: ClienteSim): void {
  guardar('clientes', { ...leer<Record<string, ClienteSim>>('clientes', {}), [c.correo]: c });
}

export function correoActual(): string {
  return leer<string>('correo', '');
}

export function identidadPendiente(): { nombre: string; correo: string } | null {
  return leer<{ nombre: string; correo: string } | null>('identidad', null);
}

export function clienteActual(): ClienteSim | undefined {
  return usuarioSimuladoActual() === 'cliente' ? clientes()[correoActual()] : undefined;
}

export function abrirSesionCliente(correo: string): void {
  guardar('correo', correo);
  fijarUsuarioSimulado('cliente');
}

export function abrirSesionPendiente(nombre: string, correo: string): void {
  guardar('correo', correo);
  guardar('identidad', { nombre, correo });
  fijarUsuarioSimulado('pendiente');
}

export function sesionDeCliente(c: ClienteSim): ResultadoAccesoDTO {
  return {
    registrado: true,
    idUsuario: c.idUsuario,
    nombre: c.nombre,
    correo: c.correo,
    tipoUsuario: 'CLIENTE',
    operaciones: [],
  };
}

/** La sesión del modo simulado, o `null` si no hay (401). */
export function sesionActual(): ResultadoAccesoDTO | null {
  const usuario = usuarioSimuladoActual();
  if (usuario === 'cliente') {
    const c = clienteActual();
    return c?.activo ? sesionDeCliente(c) : null;
  }
  if (usuario === 'pendiente') {
    const i = identidadPendiente();
    return i
      ? { registrado: false, nombre: i.nombre, correo: i.correo, tipoUsuario: '', operaciones: [] }
      : USUARIOS_SIMULADOS.pendiente;
  }
  return USUARIOS_SIMULADOS[usuario];
}

/** Falla forzada para probar estados: localStorage `chibchaweb.simulado.falla` = contingencia | inactivo. */
export function fallaForzada(): string {
  try {
    return localStorage.getItem('chibchaweb.simulado.falla') ?? '';
  } catch {
    return '';
  }
}
