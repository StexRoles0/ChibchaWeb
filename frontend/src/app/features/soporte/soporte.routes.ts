import { Route, Routes, UrlSegment, UrlMatchResult } from '@angular/router';
import { autenticado, operacion } from '../../core/guardas';

/**
 * `/soporte/bandeja` y `/soporte/tickets/:id` son la misma pantalla (M-17): con un solo `Route`
 * el componente se conserva al elegir otro ticket y la lista no se vuelve a pedir.
 */
export function bandejaMatcher(segmentos: UrlSegment[]): UrlMatchResult | null {
  if (segmentos.length === 1 && segmentos[0].path === 'bandeja') return { consumed: segmentos };
  if (segmentos.length === 2 && segmentos[0].path === 'tickets') {
    return { consumed: segmentos, posParams: { id: segmentos[1] } };
  }
  return null;
}

export const RUTA_BANDEJA: Route = {
  matcher: bandejaMatcher,
  canActivate: [operacion('ATENDER_TICKETS')],
  loadComponent: () => import('./bandeja').then((m) => m.Bandeja),
};

export const SOPORTE_ROUTES: Routes = [
  {
    path: 'reportar',
    canActivate: [autenticado],
    loadComponent: () => import('./reportar').then((m) => m.ReportarNovedad),
  },
  RUTA_BANDEJA,
];
