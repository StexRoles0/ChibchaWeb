import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DetalleDTO, DistribuidorDTO, ResumenDTO } from './dto';

/** Cuerpo del 201 de `POST /distribuidores`. */
export interface DistribuidorCreado {
  id: number;
  codigo: string;
}

/** ServicioDistribuidores (permiso GESTIONAR_DISTRIBUIDORES). */
@Injectable({ providedIn: 'root' })
export class DistribuidoresApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `GET /distribuidores?filtro=` → `consultarBasico(DISTRIBUIDOR, filtro)`. */
  listar(filtro = ''): Observable<ResumenDTO[]> {
    const params = filtro ? new HttpParams().set('filtro', filtro) : undefined;
    return this.http.get<ResumenDTO[]>(`${this.base}/distribuidores`, { params });
  }

  /** `GET /distribuidores/{id}` → `consultarDetalle(DISTRIBUIDOR, id)`. */
  detalle(id: number): Observable<DetalleDTO> {
    return this.http.get<DetalleDTO>(`${this.base}/distribuidores/${id}`);
  }

  /** `POST /distribuidores` → `crearDistribuidor(datos)`; 201 `{ id, codigo }` (RN-15). */
  crear(datos: DistribuidorDTO): Observable<DistribuidorCreado> {
    return this.http.post<DistribuidorCreado>(`${this.base}/distribuidores`, datos);
  }

  /** `PUT /distribuidores/{id}` → `modificarDistribuidor`; 204. */
  modificar(id: number, datos: DistribuidorDTO): Observable<void> {
    return this.http.put<void>(`${this.base}/distribuidores/${id}`, datos);
  }

  /** `DELETE /distribuidores/{id}` → `eliminarDistribuidor` (baja lógica); 204. */
  eliminar(id: number): Observable<void> {
    return this.http.delete<void>(`${this.base}/distribuidores/${id}`);
  }
}
