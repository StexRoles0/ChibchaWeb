import { DatosClienteDTO } from '../dto';
import { guardar, leer, borrar } from './almacen';
import {
  abrirSesionCliente,
  abrirSesionPendiente,
  clientes,
  fallaForzada,
  identidadPendiente,
  sesionActual,
  sesionDeCliente,
} from './estado';
import { registrarSim } from './clientes.simulado';
import { fijarUsuarioSimulado, USUARIOS_SIMULADOS, UsuarioSimulado } from './sesiones';
import { ErrorSim, ManejadorSim } from './tipos';

const EMPLEADOS: Record<string, UsuarioSimulado> = {
  'gestion@chibchaweb.co': 'gestion',
  'soporte@chibchaweb.co': 'soporte',
  'admin@chibchaweb.co': 'admin',
};

const noAutenticado = () =>
  new ErrorSim(401, { codigo: 'NO_AUTENTICADO', mensaje: 'No hay sesión' });

/** "laura.gomez@correo.co" → "Laura Gomez" */
export function nombreDeCorreo(correo: string): string {
  return correo
    .split('@')[0]
    .split(/[._-]+/)
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(' ');
}

export const accesoSimulado: ManejadorSim = (p) => {
  const clave = `${p.metodo} ${p.ruta}`;

  if (clave === 'GET /auth/sesion') {
    const s = sesionActual();
    if (!s) throw noAutenticado();
    return { estado: 200, cuerpo: s };
  }

  if (clave === 'GET /auth/oauth/inicio') {
    const correo = p.query.get('correo')?.trim();
    if (!correo) {
      throw new ErrorSim(400, {
        codigo: 'SOLICITUD_INVALIDA',
        mensaje: 'Con el proveedor simulado, el correo es obligatorio.',
      });
    }
    const estado = Math.random().toString(36).slice(2, 10);
    guardar('estado', estado);
    return {
      estado: 200,
      cuerpo: { url: `/auth/callback?code=dev:${encodeURIComponent(correo)}&state=${estado}` },
    };
  }

  if (clave === 'POST /auth/oauth/callback') {
    const { codigo, estado } = (p.cuerpo ?? {}) as { codigo?: string; estado?: string };
    const esperado = leer<string>('estado', '');
    borrar('estado');
    if (!codigo?.startsWith('dev:') || !estado || estado !== esperado) {
      throw new ErrorSim(401, {
        codigo: 'AUTORIZACION_FALLIDA',
        mensaje: 'No se pudo completar el acceso. Inténtalo de nuevo.',
      });
    }
    const correo = decodeURIComponent(codigo.slice(4)).trim().toLowerCase();
    if (correo === 'inactivo@correo.co' || fallaForzada() === 'inactivo') {
      throw new ErrorSim(403, {
        codigo: 'USUARIO_INACTIVO',
        mensaje: 'Tu cuenta está dada de baja.',
      });
    }
    const empleado = EMPLEADOS[correo];
    if (empleado) {
      fijarUsuarioSimulado(empleado);
      return { estado: 200, cuerpo: USUARIOS_SIMULADOS[empleado] };
    }
    const cliente = clientes()[correo];
    if (cliente) {
      if (!cliente.activo) {
        throw new ErrorSim(403, {
          codigo: 'USUARIO_INACTIVO',
          mensaje: 'Tu cuenta está dada de baja.',
        });
      }
      abrirSesionCliente(correo);
      return { estado: 200, cuerpo: sesionDeCliente(cliente) };
    }
    abrirSesionPendiente(nombreDeCorreo(correo), correo);
    return { estado: 200, cuerpo: sesionActual() };
  }

  if (clave === 'POST /auth/logout') {
    fijarUsuarioSimulado('anonimo');
    return { estado: 204 };
  }

  if (clave === 'POST /auth/registro') {
    const identidad = identidadPendiente();
    if (sesionActual()?.registrado !== false || !identidad) throw noAutenticado();
    const cliente = registrarSim(p.cuerpo as DatosClienteDTO, identidad.nombre, identidad.correo);
    abrirSesionCliente(cliente.correo);
    return { estado: 201, cuerpo: sesionDeCliente(cliente) };
  }
  return undefined;
};
