import { sesionActual } from './estado';
import { ErrorSim } from './tipos';

/** Utilidades compartidas por los manejadores simulados del último lote. */

export const noEncontrado = (que: string): ErrorSim =>
  new ErrorSim(404, { codigo: 'NO_ENCONTRADO', mensaje: `${que} no existe.` });

export const estadoInvalido = (mensaje: string): ErrorSim =>
  new ErrorSim(409, { codigo: 'ESTADO_INVALIDO', mensaje });

export const contingenciaActiva = (): ErrorSim =>
  new ErrorSim(503, {
    codigo: 'CONTINGENCIA',
    mensaje:
      'El sistema está en modo contingencia; tu operación quedó respaldada y se aplicará al restablecerse el servicio.',
  });

/** 401 sin sesión, 403 si falta la operación. Devuelve la sesión. */
export function exigirOperacion(operacion: string) {
  const s = sesionActual();
  if (!s || !s.registrado) {
    throw new ErrorSim(401, { codigo: 'NO_AUTENTICADO', mensaje: 'No hay sesión.' });
  }
  if (!s.operaciones.includes(operacion)) {
    throw new ErrorSim(403, { codigo: 'SIN_PERMISO', mensaje: 'No tienes permiso.' });
  }
  return s;
}

/** 401 sin sesión, 403 si no es cliente. */
export function exigirSesionCliente() {
  const s = sesionActual();
  if (!s || !s.registrado) {
    throw new ErrorSim(401, { codigo: 'NO_AUTENTICADO', mensaje: 'No hay sesión.' });
  }
  if (s.tipoUsuario !== 'CLIENTE') {
    throw new ErrorSim(403, { codigo: 'SIN_PERMISO', mensaje: 'No tienes permiso.' });
  }
  return s;
}

export function exigirAutenticado() {
  const s = sesionActual();
  if (!s || !s.registrado) {
    throw new ErrorSim(401, { codigo: 'NO_AUTENTICADO', mensaje: 'No hay sesión.' });
  }
  return s;
}

export const dosDigitos = (n: number): string => String(n).padStart(2, '0');

/** Fecha local `AAAA-MM-DD` de un instante ISO. */
export function fechaLocalDe(iso: string): string {
  const d = new Date(iso);
  return `${d.getFullYear()}-${dosDigitos(d.getMonth() + 1)}-${dosDigitos(d.getDate())}`;
}

/** `AAAA-MM-DD HH:MM` local, formato de `movimiento`. */
export function fechaHoraLocal(d = new Date()): string {
  return `${fechaLocalDe(d.toISOString())} ${dosDigitos(d.getHours())}:${dosDigitos(d.getMinutes())}`;
}
