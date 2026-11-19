import { Routes } from '@angular/router';
import { datosCompletos, planCompleto } from './pasos.guardas';
import { RegistroLayout } from './registro-layout';
import { RegistroStore } from './registro.store';

export const REGISTRO_ROUTES: Routes = [
  {
    path: '',
    component: RegistroLayout,
    providers: [RegistroStore],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'datos' },
      {
        path: 'datos',
        loadComponent: () => import('./registro-datos').then((m) => m.RegistroDatos),
      },
      {
        path: 'plan',
        canActivate: [datosCompletos],
        loadComponent: () => import('./registro-plan').then((m) => m.RegistroPlan),
      },
      {
        path: 'pago',
        canActivate: [planCompleto],
        loadComponent: () => import('./registro-pago').then((m) => m.RegistroPago),
      },
    ],
  },
];
