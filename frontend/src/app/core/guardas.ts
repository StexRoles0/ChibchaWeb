import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SesionStore } from './auth/sesion.store';

/** Solo sin sesión: con sesión manda al inicio del rol. */
export const sinSesion: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  return sesion.sesion() === null ? true : router.parseUrl(sesion.rutaInicio());
};

export const autenticado: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  return sesion.autenticada() ? true : router.parseUrl(sesion.rutaInicio());
};

export const esCliente: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  if (sesion.esCliente()) return true;
  return router.parseUrl(sesion.autenticada() ? '/no-autorizado' : sesion.rutaInicio());
};

export const identidadPendiente: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  const router = inject(Router);
  return sesion.identidadPendiente() ? true : router.parseUrl(sesion.rutaInicio());
};

/** Exige una operación de la sesión (p. ej. 'GESTIONAR_EMPLEADOS'). */
export const operacion = (nombre: string): CanActivateFn => {
  return () => {
    const sesion = inject(SesionStore);
    const router = inject(Router);
    if (sesion.autenticada() && sesion.tieneOperacion(nombre)) return true;
    return router.parseUrl(sesion.autenticada() ? '/no-autorizado' : sesion.rutaInicio());
  };
};

/** Para la ruta raíz: redirige al inicio del rol. */
export const irAInicio: CanActivateFn = () => {
  const sesion = inject(SesionStore);
  return inject(Router).parseUrl(sesion.rutaInicio());
};
