import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { RegistroStore } from './registro.store';

/** M-03 solo si ya se llenó M-02. */
export const datosCompletos: CanActivateFn = () =>
  inject(RegistroStore).datosCompletos() ? true : inject(Router).parseUrl('/registro/datos');

/** M-04 solo si ya se eligió paquete y plan. */
export const planCompleto: CanActivateFn = () => {
  const store = inject(RegistroStore);
  const router = inject(Router);
  if (!store.datosCompletos()) return router.parseUrl('/registro/datos');
  return store.planCompleto() ? true : router.parseUrl('/registro/plan');
};
