import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DetalleDTO, EmpleadoDTO, ResumenDTO } from './dto';

/** Cuerpo del 201 de `POST /empleados`. */
export interface EmpleadoCreado {
  id: number;
}

/** ServicioEmpleados (permiso GESTIONAR_EMPLEADOS). */
@Injectable({ providedIn: 'root' })
export class EmpleadosApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `GET /catalogo/roles` → `consultarRoles()` (id, titulo = nombre del cargo). */
  roles(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/catalogo/roles`);
  }

  /** `GET /empleados?filtro=` → `consultarBasico(EMPLEADO, filtro)`. */
  listar(filtro = ''): Observable<ResumenDTO[]> {
    const params = filtro ? new HttpParams().set('filtro', filtro) : undefined;
    return this.http.get<ResumenDTO[]>(`${this.base}/empleados`, { params });
  }

  /** `GET /empleados/{id}` → `consultarDetalle(EMPLEADO, id)`. */
  detalle(id: number): Observable<DetalleDTO> {
    return this.http.get<DetalleDTO>(`${this.base}/empleados/${id}`);
  }

  /** `POST /empleados` → `crearEmpleado(datos)`; 201 `{ id }`. */
  crear(datos: EmpleadoDTO): Observable<EmpleadoCreado> {
    return this.http.post<EmpleadoCreado>(`${this.base}/empleados`, datos);
  }

  /** `PUT /empleados/{id}` → `modificarEmpleado`; 204. */
  modificar(id: number, datos: EmpleadoDTO): Observable<void> {
    return this.http.put<void>(`${this.base}/empleados/${id}`, datos);
  }

  /** `DELETE /empleados/{id}` → `eliminarEmpleado` (baja lógica); 204. */
  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/empleados/${id}`);
  }
}
