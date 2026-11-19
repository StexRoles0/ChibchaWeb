import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DetalleDTO, ResumenDTO } from './dto';

export type TipoEntidad = 'CLIENTE' | 'EMPLEADO' | 'DISTRIBUIDOR' | 'TICKET';

/** ServicioConsultas: CLIENTE/EMPLEADO/DISTRIBUIDOR con CONSULTAR_REGISTROS; TICKET con ATENDER_TICKETS. */
@Injectable({ providedIn: 'root' })
export class ConsultasApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `GET /consultas/{tipoEntidad}?filtro=` → `consultarBasico`. */
  basico(tipo: TipoEntidad, filtro = ''): Observable<ResumenDTO[]> {
    const params = filtro ? new HttpParams().set('filtro', filtro) : undefined;
    return this.http.get<ResumenDTO[]>(`${this.base}/consultas/${tipo}`, { params });
  }

  /** `GET /consultas/{tipoEntidad}/{id}` → `consultarDetalle`. */
  detalle(tipo: TipoEntidad, id: number): Observable<DetalleDTO> {
    return this.http.get<DetalleDTO>(`${this.base}/consultas/${tipo}/${id}`);
  }
}
