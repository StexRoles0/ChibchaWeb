import { ResultadoAccesoDTO } from '../dto';

export type UsuarioSimulado = 'cliente' | 'gestion' | 'soporte' | 'admin' | 'pendiente' | 'anonimo';

export const USUARIOS_SIMULADOS: Record<UsuarioSimulado, ResultadoAccesoDTO | null> = {
  cliente: {
    registrado: true,
    idUsuario: 1,
    nombre: 'Steven Navarro',
    correo: 'steven@correo.co',
    tipoUsuario: 'CLIENTE',
    operaciones: [],
  },
  gestion: {
    registrado: true,
    idUsuario: 2,
    nombre: 'Luis Pérez',
    correo: 'gestion@chibchaweb.co',
    tipoUsuario: 'EMPLEADO',
    rol: 'Gestión',
    operaciones: ['GESTIONAR_EMPLEADOS', 'GESTIONAR_DISTRIBUIDORES', 'CONSULTAR_REGISTROS'],
  },
  soporte: {
    registrado: true,
    idUsuario: 3,
    nombre: 'Ana Ruiz',
    correo: 'soporte@chibchaweb.co',
    tipoUsuario: 'EMPLEADO',
    rol: 'Soporte',
    operaciones: ['ATENDER_TICKETS'],
  },
  admin: {
    registrado: true,
    idUsuario: 4,
    nombre: 'Marta Rojas',
    correo: 'admin@chibchaweb.co',
    tipoUsuario: 'EMPLEADO',
    rol: 'Administrador',
    operaciones: ['MIGRAR_DATOS', 'GESTIONAR_CONTINGENCIA'],
  },
  pendiente: {
    registrado: false,
    nombre: 'Laura Gómez',
    correo: 'laura@correo.co',
    tipoUsuario: '',
    operaciones: [],
  },
  anonimo: null,
};

const CLAVE = 'chibchaweb.simulado.usuario';

export function usuarioSimuladoActual(): UsuarioSimulado {
  try {
    const v = localStorage.getItem(CLAVE) as UsuarioSimulado | null;
    return v && v in USUARIOS_SIMULADOS ? v : 'anonimo';
  } catch {
    return 'anonimo';
  }
}

export function fijarUsuarioSimulado(usuario: UsuarioSimulado): void {
  try {
    localStorage.setItem(CLAVE, usuario);
  } catch {
    // sin almacenamiento: se queda el valor por defecto
  }
}
