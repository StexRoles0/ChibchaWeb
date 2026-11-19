import { Routes } from '@angular/router';
import { esCliente } from '../../core/guardas';
import { PerfilStore } from './perfil.store';

export const CLIENTE_ROUTES: Routes = [
  {
    path: '',
    canActivate: [esCliente],
    providers: [PerfilStore],
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () => import('./inicio').then((m) => m.InicioCliente),
      },
      {
        path: 'perfil/editar',
        loadComponent: () => import('./editar').then((m) => m.EditarPerfil),
      },
      {
        // M-06; el hijo `eliminar` abre el diálogo M-08 sobre la misma pantalla.
        path: 'perfil',
        loadComponent: () => import('./perfil').then((m) => m.Perfil),
        children: [{ path: 'eliminar', children: [] }],
      },
      {
        path: 'dominios',
        loadComponent: () => import('./dominios').then((m) => m.Dominios),
      },
      {
        path: 'soporte',
        loadComponent: () => import('../soporte/reportar').then((m) => m.ReportarNovedad),
      },
    ],
  },
];
