import { inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';
import { DistribuidoresApi } from '../../core/api/distribuidores.api';
import { DetalleDTO, ResumenDTO } from '../../core/api/dto';
import { EmpleadosApi } from '../../core/api/empleados.api';

/** M-12/M-13/M-14 sirven a empleados y distribuidores; la ruta indica cuál (`data.tipo`). */
export type TipoPersonal = 'empleado' | 'distribuidor';

export interface ConfigPersonal {
  tipo: TipoPersonal;
  singular: string;
  plural: string;
  /** Ruta Angular del listado, también base de `nuevo`, `:id` y `:id/editar`. */
  ruta: string;
  articulo: 'el' | 'la';
}

const CONFIG: Record<TipoPersonal, ConfigPersonal> = {
  empleado: {
    tipo: 'empleado',
    singular: 'empleado',
    plural: 'Empleados',
    ruta: '/gestion/empleados',
    articulo: 'el',
  },
  distribuidor: {
    tipo: 'distribuidor',
    singular: 'distribuidor',
    plural: 'Distribuidores',
    ruta: '/gestion/distribuidores',
    articulo: 'el',
  },
};

/** Lee `data.tipo` de la ruta activa. */
export function configDeRuta(): ConfigPersonal {
  const tipo = inject(ActivatedRoute).snapshot.data['tipo'] as TipoPersonal | undefined;
  return CONFIG[tipo ?? 'empleado'];
}

/** Las operaciones comunes (mismas firmas) de `EmpleadosApi` y `DistribuidoresApi`. */
export interface ApiPersonal {
  listar(filtro?: string): Observable<ResumenDTO[]>;
  detalle(id: number): Observable<DetalleDTO>;
  eliminar(id: number): Observable<void>;
}

export function apiDeTipo(tipo: TipoPersonal): ApiPersonal {
  const empleados = inject(EmpleadosApi);
  const distribuidores = inject(DistribuidoresApi);
  return tipo === 'empleado' ? empleados : distribuidores;
}

export const esActivo = (estado: string): boolean => estado.toUpperCase() === 'ACTIVO';
