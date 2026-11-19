import { HttpErrorResponse, HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { mergeMap, of, throwError, timer } from 'rxjs';
import { delay } from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import { accesoSimulado } from './acceso.simulado';
import { adminSimulado } from './admin.simulado';
import { catalogoSimulado } from './catalogo.simulado';
import { clientesSimulado } from './clientes.simulado';
import { dominiosSimulado } from './dominios.simulado';
import { gestionSimulado } from './gestion.simulado';
import { soporteSimulado } from './soporte.simulado';
import { ErrorSim, ManejadorSim } from './tipos';

const MANEJADORES: ManejadorSim[] = [
  accesoSimulado,
  catalogoSimulado,
  clientesSimulado,
  gestionSimulado,
  dominiosSimulado,
  soporteSimulado,
  adminSimulado,
];

/** Respuestas simuladas para trabajar sin backend. Solo actúa si environment.simularApi. */
export const simuladoInterceptor: HttpInterceptorFn = (req, next) => {
  if (!environment.simularApi || !req.url.startsWith(environment.apiBase)) return next(req);

  const peticion = {
    metodo: req.method,
    ruta: req.url.slice(environment.apiBase.length).split('?')[0],
    query: new URL(req.urlWithParams, 'http://simulado').searchParams,
    cuerpo: req.body,
  };

  try {
    for (const manejar of MANEJADORES) {
      const r = manejar(peticion);
      if (r) {
        return of(new HttpResponse({ status: r.estado, body: r.cuerpo ?? null })).pipe(delay(120));
      }
    }
  } catch (e) {
    if (e instanceof ErrorSim) {
      return timer(120).pipe(
        mergeMap(() =>
          throwError(
            () => new HttpErrorResponse({ status: e.estado, url: req.url, error: e.cuerpo }),
          ),
        ),
      );
    }
    throw e;
  }
  return next(req);
};
