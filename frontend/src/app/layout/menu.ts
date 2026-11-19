export interface ItemMenu {
  etiqueta: string;
  ruta: string;
  /** Si se indica, el ítem solo aparece cuando la sesión tiene esa operación. */
  operacion?: string;
  exacto?: boolean;
}

const REPORTAR: ItemMenu = { etiqueta: 'Reportar novedad', ruta: '/soporte/reportar' };

/** Menú lateral por rol (docs/ui.md §Navegación). */
export function menuPara(tipoUsuario: string, rol: string | undefined): ItemMenu[] {
  if (tipoUsuario === 'CLIENTE') {
    return [
      { etiqueta: 'Inicio', ruta: '/cliente', exacto: true },
      { etiqueta: 'Mi perfil', ruta: '/cliente/perfil' },
      { etiqueta: 'Dominios', ruta: '/cliente/dominios' },
      { etiqueta: 'Soporte', ruta: '/cliente/soporte' },
    ];
  }
  switch (rol) {
    case 'Gestión':
      return [
        { etiqueta: 'Inicio', ruta: '/gestion', exacto: true, operacion: 'GESTIONAR_EMPLEADOS' },
        { etiqueta: 'Empleados', ruta: '/gestion/empleados', operacion: 'GESTIONAR_EMPLEADOS' },
        {
          etiqueta: 'Distribuidores',
          ruta: '/gestion/distribuidores',
          operacion: 'GESTIONAR_DISTRIBUIDORES',
        },
        { etiqueta: 'Clientes', ruta: '/gestion/clientes', operacion: 'CONSULTAR_REGISTROS' },
        REPORTAR,
      ];
    case 'Soporte':
      return [
        { etiqueta: 'Bandeja de tickets', ruta: '/soporte/bandeja', operacion: 'ATENDER_TICKETS' },
        REPORTAR,
      ];
    case 'Administrador':
      return [
        { etiqueta: 'Inicio', ruta: '/admin', exacto: true, operacion: 'MIGRAR_DATOS' },
        { etiqueta: 'Migración', ruta: '/admin/migracion', operacion: 'MIGRAR_DATOS' },
        {
          etiqueta: 'Contingencia',
          ruta: '/admin/contingencia',
          operacion: 'GESTIONAR_CONTINGENCIA',
        },
        REPORTAR,
      ];
    default:
      return [];
  }
}

export function etiquetaRol(tipoUsuario: string, rol: string | undefined): string {
  if (tipoUsuario === 'CLIENTE') return 'Cliente';
  if (rol === 'Gestión') return 'Empleado de gestión';
  if (rol === 'Soporte') return 'Empleado de soporte';
  return rol ?? '';
}

export function iniciales(nombre: string): string {
  return nombre
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('');
}
