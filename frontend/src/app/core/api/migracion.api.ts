import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ResultadoMigracionDTO } from './dto';

export type EstadoMigracion = 'EJECUTADA' | 'REVERTIDA' | 'CANCELADA';

/** ServicioMigracion (permiso MIGRAR_DATOS). */
@Injectable({ providedIn: 'root' })
export class MigracionApi {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBase;

  /** `POST /migraciones` → `migrarRegistrosLegados(idSesion)` (simulación); 201. */
  simular(): Observable<ResultadoMigracionDTO> {
    return this.http.post<ResultadoMigracionDTO>(`${this.base}/migraciones`, {});
  }

  /** `POST /migraciones/{id}/confirmacion` → `confirmarMigracion`; `EJECUTADA` o `REVERTIDA`. */
  confirmar(id: number): Observable<{ estado: EstadoMigracion }> {
    return this.http.post<{ estado: EstadoMigracion }>(
      `${this.base}/migraciones/${id}/confirmacion`,
      {},
    );
  }

  /** `POST /migraciones/{id}/cancelacion` → `cancelarMigracion`; `CANCELADA`. */
  cancelar(id: number): Observable<{ estado: EstadoMigracion }> {
    return this.http.post<{ estado: EstadoMigracion }>(
      `${this.base}/migraciones/${id}/cancelacion`,
      {},
    );
  }
}
