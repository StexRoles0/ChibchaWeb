import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { SesionStore } from './auth/sesion.store';
import { ContingenciaStore } from './contingencia.store';
import { credencialesInterceptor, erroresInterceptor } from './interceptores';
import { USUARIOS_SIMULADOS } from './api/simulado/sesiones';

describe('interceptores', () => {
  let http: HttpClient;
  let ctrl: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([credencialesInterceptor, erroresInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    ctrl = TestBed.inject(HttpTestingController);
  });

  it('manda las credenciales a la API', () => {
    http.get('/api/v1/x').subscribe();
    const req = ctrl.expectOne('/api/v1/x');
    expect(req.request.withCredentials).toBe(true);
    req.flush({});
  });

  it('401 limpia la sesión y manda a /acceso', () => {
    const router = TestBed.inject(Router);
    const nav = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    const sesion = TestBed.inject(SesionStore);
    sesion.establecer(USUARIOS_SIMULADOS.cliente);
    http.get('/api/v1/clientes/me').subscribe({ error: () => undefined });
    ctrl
      .expectOne('/api/v1/clientes/me')
      .flush({ codigo: 'NO_AUTENTICADO' }, { status: 401, statusText: 'x' });
    expect(sesion.sesion()).toBeNull();
    expect(nav).toHaveBeenCalledWith('/acceso');
  });

  it('503 CONTINGENCIA activa el banner y entrega ErrorApi', () => {
    let error: unknown;
    http.post('/api/v1/tickets', {}).subscribe({ error: (e) => (error = e) });
    ctrl
      .expectOne('/api/v1/tickets')
      .flush({ codigo: 'CONTINGENCIA', mensaje: 'm' }, { status: 503, statusText: 'x' });
    expect(TestBed.inject(ContingenciaStore).activa()).toBe(true);
    expect(error).toMatchObject({ codigo: 'CONTINGENCIA', estado: 503 });
  });

  it('422 conserva el campo para mostrarlo bajo el input', () => {
    let error: unknown;
    http.post('/api/v1/auth/registro', {}).subscribe({ error: (e) => (error = e) });
    ctrl
      .expectOne('/api/v1/auth/registro')
      .flush(
        { codigo: 'VALIDACION', mensaje: 'La tarjeta está vencida', campo: 'vencimiento' },
        { status: 422, statusText: 'x' },
      );
    expect(error).toMatchObject({ campo: 'vencimiento', mensaje: 'La tarjeta está vencida' });
  });

  it('el callback OAuth no redirige: lo maneja su pantalla (401 y 403 USUARIO_INACTIVO)', () => {
    const nav = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const errores: unknown[] = [];
    http.post('/api/v1/auth/oauth/callback', {}).subscribe({ error: (e) => errores.push(e) });
    ctrl
      .expectOne('/api/v1/auth/oauth/callback')
      .flush({ codigo: 'AUTORIZACION_FALLIDA', mensaje: 'x' }, { status: 401, statusText: 'x' });
    http.post('/api/v1/auth/oauth/callback', {}).subscribe({ error: (e) => errores.push(e) });
    ctrl
      .expectOne('/api/v1/auth/oauth/callback')
      .flush({ codigo: 'USUARIO_INACTIVO', mensaje: 'y' }, { status: 403, statusText: 'x' });
    expect(nav).not.toHaveBeenCalled();
    expect(errores).toMatchObject([
      { codigo: 'AUTORIZACION_FALLIDA' },
      { codigo: 'USUARIO_INACTIVO' },
    ]);
  });
});
