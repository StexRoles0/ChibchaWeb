import { Routes } from '@angular/router';
import { operacion } from '../../core/guardas';

const EMP = { canActivate: [operacion('GESTIONAR_EMPLEADOS')] };
const DIS = { canActivate: [operacion('GESTIONAR_DISTRIBUIDORES')] };
const CON = { canActivate: [operacion('CONSULTAR_REGISTROS')] };

const empleado = { tipo: 'empleado' };
const distribuidor = { tipo: 'distribuidor' };

const listado = () => import('./listado').then((m) => m.ListadoPersonal);
const formulario = () => import('./formulario').then((m) => m.FormularioPersonal);
const detalle = () => import('./detalle').then((m) => m.DetallePersonal);

/** M-11 a M-16. `nuevo` va antes que `:id` para que no se tome como identificador. */
export const GESTION_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    ...EMP,
    loadComponent: () => import('./inicio').then((m) => m.InicioGestion),
  },
  { path: 'empleados', pathMatch: 'full', ...EMP, data: empleado, loadComponent: listado },
  { path: 'empleados/nuevo', ...EMP, data: empleado, loadComponent: formulario },
  { path: 'empleados/:id/editar', ...EMP, data: empleado, loadComponent: formulario },
  { path: 'empleados/:id', ...EMP, data: empleado, loadComponent: detalle },
  { path: 'distribuidores', pathMatch: 'full', ...DIS, data: distribuidor, loadComponent: listado },
  { path: 'distribuidores/nuevo', ...DIS, data: distribuidor, loadComponent: formulario },
  { path: 'distribuidores/:id/editar', ...DIS, data: distribuidor, loadComponent: formulario },
  { path: 'distribuidores/:id', ...DIS, data: distribuidor, loadComponent: detalle },
  {
    path: 'clientes',
    ...CON,
    loadComponent: () => import('./clientes').then((m) => m.ClientesGestion),
  },
];
