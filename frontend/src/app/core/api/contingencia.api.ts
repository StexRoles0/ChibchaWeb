import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ResumenDTO } from './dto';

export const ALGORITMOS = ['AES', 'ChaCha20', 'Camellia', 'Twofish'] as const;
export type Algoritmo = (typeof ALGORITMOS)[number];

/** ServicioContingencia (permiso GESTIONAR_CONTINGENCIA). */
@Injectable({ providedIn: 'root' })
export class ContingenciaApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `GET /contingencia/pendientes` → `consultarRespaldoPendiente` (titulo = tipoEvento, subtitulo = algoritmo). */
  pendientes(): Observable<ResumenDTO[]> {
    return this.http.get<ResumenDTO[]>(`${this.base}/contingencia/pendientes`);
  }

  /** `PUT /contingencia/algoritmo` → `cambiarAlgoritmoCifrado`; 204. */
  cambiarAlgoritmo(nombre: Algoritmo): Observable<void> {
    return this.http.put<void>(`${this.base}/contingencia/algoritmo`, { nombre });
  }

  /** `POST /contingencia/sincronizacion` → `sincronizarRespaldo`. */
  sincronizar(): Observable<{ sincronizados: number }> {
    return this.http.post<{ sincronizados: number }>(
      `${this.base}/contingencia/sincronizacion`,
      {},
    );
  }
}
