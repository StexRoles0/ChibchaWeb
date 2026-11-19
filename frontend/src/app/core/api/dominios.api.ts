import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ResumenDTO } from './dto';

export const EXTENSIONES_DOMINIO = ['.com', '.co', '.net', '.org'] as const;
export type ExtensionDominio = (typeof EXTENSIONES_DOMINIO)[number];

/** Cuerpo de `POST /dominios/solicitudes`. */
export interface SolicitudDominioDTO {
  nombre: string;
  extension: ExtensionDominio;
}

/** Cuerpo del 201: `ENVIADA` o `FALLIDA` (registrador caído o que rechaza). */
export interface SolicitudRegistrada {
  id: number;
  estado: string;
}

/** ServicioDominios (permiso EsCliente). */
@Injectable({ providedIn: 'root' })
export class DominiosApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `POST /dominios/solicitudes` → `registrarSolicitudDominio` y `generarYEnviarSolicitudXML`; 201. */
  solicitar(datos: SolicitudDominioDTO): Observable<SolicitudRegistrada> {
    return this.http.post<SolicitudRegistrada>(`${this.base}/dominios/solicitudes`, datos);
  }

  /** `GET /dominios/solicitudes` → `consultarSolicitudes(idSesion)` (titulo = nombre completo). */
  solicitudes(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/dominios/solicitudes`);
  }
}
