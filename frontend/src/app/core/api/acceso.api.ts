import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DatosClienteDTO, ResultadoAccesoDTO, ResumenDTO } from './dto';

/** Cuerpo de `POST /auth/oauth/callback`. */
export interface CallbackOAuth {
  codigo: string;
  estado: string;
}

/** ServicioAcceso: acceso, sesión, registro y catálogo del registro. */
@Injectable({ providedIn: 'root' })
export class AccesoApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `GET /auth/oauth/inicio[?correo=]` → URL a la que hay que redirigir. */
  oauthInicio(correo?: string): Observable<{ url: string }> {
    const params = correo ? new HttpParams().set('correo', correo) : undefined;
    return this.http.get<{ url: string }>(`${this.base}/auth/oauth/inicio`, { params });
  }

  /** `POST /auth/oauth/callback` → `iniciarSesion(codigo)`. */
  callback(cuerpo: CallbackOAuth): Observable<ResultadoAccesoDTO> {
    return this.http.post<ResultadoAccesoDTO>(`${this.base}/auth/oauth/callback`, cuerpo);
  }

  sesion(): Observable<ResultadoAccesoDTO> {
    return this.http.get<ResultadoAccesoDTO>(`${this.base}/auth/sesion`);
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.base}/auth/logout`, {});
  }

  /** `GET /catalogo/paquetes` → `consultarPaquetes()` (subtitulo = "10.00"). */
  paquetes(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/catalogo/paquetes`);
  }

  /** `GET /catalogo/planes` → `consultarPlanes()` (subtitulo = "3|0.05"). */
  planes(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/catalogo/planes`);
  }

  /** `POST /auth/registro` → `registrarse(datos)`; 201 con la sesión ya abierta. */
  registro(datos: DatosClienteDTO): Observable<ResultadoAccesoDTO> {
    return this.http.post<ResultadoAccesoDTO>(`${this.base}/auth/registro`, datos);
  }
}
