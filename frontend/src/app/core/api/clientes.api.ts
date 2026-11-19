import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DatosClienteDTO, DetalleDTO, ResumenDTO } from './dto';

export type CategoriaPerfil = 'PERSONAL' | 'PAQUETE_PLAN' | 'PAGO';

/** ServicioClientes: el perfil del cliente en sesión. */
@Injectable({ providedIn: 'root' })
export class ClientesApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `GET /clientes/me` → `consultarDetalle(CLIENTE, idSesion)`. */
  detalle(): Observable<DetalleDTO> {
    return this.http.get<DetalleDTO>(`${this.base}/clientes/me`);
  }

  /** `PATCH /clientes/me?categoria=` → `modificarPerfil`; 204. Solo el bloque de la pestaña. */
  modificar(categoria: CategoriaPerfil, datos: Partial<DatosClienteDTO>): Observable<void> {
    return this.http.patch<void>(`${this.base}/clientes/me`, datos, {
      params: new HttpParams().set('categoria', categoria),
    });
  }

  /** `DELETE /clientes/me` → `eliminarPerfil`; 204 y cierra la sesión. */
  eliminar(): Observable<void> {
    return this.http.delete<void>(`${this.base}/clientes/me`);
  }

  /** `GET /clientes/me/sitios` → `consultarSitios(idSesion)` (P-06; titulo = subdominio). */
  sitios(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/clientes/me/sitios`);
  }
}
