import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { environment } from '../../environments/environment';
import { SesionStore } from './auth/sesion.store';
import { ContingenciaStore } from './contingencia.store';
import { aErrorApi } from './errores';

/** Manda la cookie de sesión en las peticiones a la API. */
export const credencialesInterceptor: HttpInterceptorFn = (req, next) =>
  req.url.startsWith(environment.apiBase) ? next(req.clone({ withCredentials: true })) : next(req);

/** 401 → /acceso, 403 → /no-autorizado, 503 → banner de contingencia (salvo el callback OAuth). */
export const erroresInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const sesion = inject(SesionStore);
  const contingencia = inject(ContingenciaStore);

  return next(req).pipe(
    catchError((err: HttpErrorResponse) => {
      const error = aErrorApi(err);
      // GET /auth/sesion sin sesión es normal al arrancar: no redirige.
      const esConsultaSesion = req.url.endsWith('/auth/sesion');
      // El callback OAuth lo maneja su pantalla: muestra el error en M-01 (401 y 403 USUARIO_INACTIVO).
      if (req.url.endsWith('/auth/oauth/callback')) {
        return throwError(() => error);
      }
      if (err.status === 401 && !esConsultaSesion) {
        sesion.establecer(null);
        void router.navigateByUrl('/acceso');
      } else if (err.status === 403) {
        void router.navigateByUrl('/no-autorizado');
      } else if (err.status === 503 && error.codigo === 'CONTINGENCIA') {
        contingencia.activar(error.mensaje);
      }
      return throwError(() => error);
    }),
  );
};
