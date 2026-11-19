import { Routes } from '@angular/router';
import { autenticado, identidadPendiente, irAInicio, sinSesion } from './core/guardas';

export const routes: Routes = [
  { path: '', pathMatch: 'full', canActivate: [irAInicio], children: [] },
  {
    path: 'acceso',
    canActivate: [sinSesion],
    loadChildren: () => import('./features/acceso/acceso.routes').then((m) => m.ACCESO_ROUTES),
  },
  {
    path: 'auth/callback',
    loadComponent: () => import('./features/acceso/callback').then((m) => m.Callback),
  },
  {
    path: 'registro',
    canActivate: [identidadPendiente],
    loadChildren: () =>
      import('./features/registro/registro.routes').then((m) => m.REGISTRO_ROUTES),
  },
  {
    path: '',
    canActivate: [autenticado],
    loadComponent: () => import('./layout/shell').then((m) => m.Shell),
    children: [
      {
        path: 'cliente',
        loadChildren: () =>
          import('./features/cliente/cliente.routes').then((m) => m.CLIENTE_ROUTES),
      },
      {
        path: 'soporte',
        loadChildren: () =>
          import('./features/soporte/soporte.routes').then((m) => m.SOPORTE_ROUTES),
      },
      {
        path: 'gestion',
        loadChildren: () =>
          import('./features/gestion/gestion.routes').then((m) => m.GESTION_ROUTES),
      },
      {
        path: 'admin',
        loadChildren: () => import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES),
      },
      {
        path: 'no-autorizado',
        loadComponent: () => import('./shared/no-autorizado').then((m) => m.NoAutorizado),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
