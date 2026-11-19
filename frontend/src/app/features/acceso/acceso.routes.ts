import { Routes } from '@angular/router';

export const ACCESO_ROUTES: Routes = [
  { path: '', pathMatch: 'full', loadComponent: () => import('./acceso').then((m) => m.Acceso) },
];
