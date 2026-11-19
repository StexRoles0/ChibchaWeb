import { Routes } from '@angular/router';
import { operacion } from '../../core/guardas';
import { MigracionStore } from './migracion.store';

/** M-18 a M-20. El estado de la migración vive mientras se está en el área de administración. */
export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    providers: [MigracionStore],
    children: [
      {
        path: '',
        pathMatch: 'full',
        canActivate: [operacion('MIGRAR_DATOS')],
        loadComponent: () => import('./inicio').then((m) => m.InicioAdmin),
      },
      {
        path: 'migracion',
        canActivate: [operacion('MIGRAR_DATOS')],
        loadComponent: () => import('./migracion').then((m) => m.Migracion),
      },
      {
        path: 'contingencia',
        canActivate: [operacion('GESTIONAR_CONTINGENCIA')],
        loadComponent: () => import('./contingencia').then((m) => m.Contingencia),
      },
    ],
  },
];
