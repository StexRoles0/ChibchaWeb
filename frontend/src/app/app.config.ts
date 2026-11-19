import { provideHttpClient, withInterceptors, withXsrfConfiguration } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { simuladoInterceptor } from './core/api/simulado/simulado.interceptor';
import { SesionStore } from './core/auth/sesion.store';
import { credencialesInterceptor, erroresInterceptor } from './core/interceptores';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(
      // El simulado va al final: así los errores simulados pasan por el interceptor de errores.
      withInterceptors([credencialesInterceptor, erroresInterceptor, simuladoInterceptor]),
      withXsrfConfiguration({ cookieName: 'csrftoken', headerName: 'X-CSRFToken' }),
    ),
    // La sesión se conoce antes de resolver las guardas.
    provideAppInitializer(() => inject(SesionStore).cargar()),
  ],
};
