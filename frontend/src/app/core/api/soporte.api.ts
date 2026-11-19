import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DetalleDTO, ResumenDTO } from './dto';

/** Cuerpo de `POST /tickets`. `idSitio` solo lo envían los clientes. */
export interface TicketNuevoDTO {
  categoria: string;
  descripcion: string;
  idSitio?: number;
}

/** Cuerpo de `POST /tickets/{id}/enrutamiento`. */
export interface EnrutamientoDTO {
  escalar: boolean;
  observacion: string;
}

/** ServicioSoporte. */
@Injectable({ providedIn: 'root' })
export class SoporteApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `POST /tickets` → `registrarTicket`; 201 `{ id }`. */
  crear(datos: TicketNuevoDTO): Observable<{ id: number }> {
    return this.http.post<{ id: number }>(`${this.base}/tickets`, datos);
  }

  /** `GET /tickets/mios` → `consultarMisTickets`. */
  mios(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/tickets/mios`);
  }

  /** `GET /tickets/diarios?fecha=AAAA-MM-DD` → `consultarTicketsDiario` (ATENDER_TICKETS). */
  diarios(fecha: string): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/tickets/diarios`, {
      params: new HttpParams().set('fecha', fecha),
    });
  }

  /** `GET /tickets/{id}` → `consultarDetalle(TICKET, id)` (ATENDER_TICKETS). */
  detalle(id: number): Observable<DetalleDTO> {
    return this.http.get<DetalleDTO>(`${this.base}/tickets/${id}`);
  }

  /** `POST /tickets/{id}/enrutamiento` → `enrutarPorNivelServicio`; 204. */
  enrutar(id: number, datos: EnrutamientoDTO): Observable<void> {
    return this.http.post<void>(`${this.base}/tickets/${id}/enrutamiento`, datos);
  }
}
