import { HttpErrorResponse } from '@angular/common/http';

/** Cuerpo de error único de docs/api.md. */
export interface ErrorApi {
  codigo: string;
  mensaje: string;
  campo?: string;
  estado: number;
}

const MENSAJES: Record<string, string> = {
  NO_AUTENTICADO: 'Tu sesión terminó. Ingresa de nuevo.',
  AUTORIZACION_FALLIDA: 'No se pudo completar el acceso. Inténtalo de nuevo.',
  SIN_PERMISO: 'No tienes permiso para realizar esta acción.',
  USUARIO_INACTIVO: 'Tu cuenta está dada de baja.',
  NO_ENCONTRADO: 'No encontramos lo que buscas.',
  DUPLICADO: 'Ese registro ya existe.',
  ESTADO_INVALIDO: 'La operación no es válida en el estado actual.',
  SUBDOMINIO_EN_USO: 'Ese subdominio ya está en uso.',
  CONTINGENCIA:
    'El sistema está en modo contingencia; tu operación quedó respaldada y se aplicará al restablecerse el servicio.',
  SOLICITUD_INVALIDA: 'La solicitud no es válida.',
};

export function aErrorApi(err: HttpErrorResponse): ErrorApi {
  const cuerpo = (err.error ?? {}) as Partial<ErrorApi>;
  const codigo = cuerpo.codigo ?? (err.status === 0 ? 'SIN_CONEXION' : 'ERROR');
  return {
    codigo,
    estado: err.status,
    campo: cuerpo.campo,
    mensaje:
      cuerpo.mensaje ??
      MENSAJES[codigo] ??
      (err.status === 0
        ? 'No hay conexión con el servidor.'
        : 'Ocurrió un error inesperado. Inténtalo de nuevo.'),
  };
}

export function mensajeDe(codigo: string): string | undefined {
  return MENSAJES[codigo];
}
