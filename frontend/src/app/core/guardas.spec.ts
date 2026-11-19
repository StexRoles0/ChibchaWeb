import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, UrlTree } from '@angular/router';
import { ResultadoAccesoDTO } from './api/dto';
import { USUARIOS_SIMULADOS } from './api/simulado/sesiones';
import { SesionStore } from './auth/sesion.store';
import { autenticado, esCliente, identidadPendiente, operacion, sinSesion } from './guardas';

function ejecutar(guarda: ReturnType<typeof operacion>, sesion: ResultadoAccesoDTO | null) {
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({ providers: [provideRouter([])] });
  TestBed.inject(SesionStore).establecer(sesion);
  const r = TestBed.runInInjectionContext(() => guarda({} as never, {} as never));
  return r instanceof UrlTree ? TestBed.inject(Router).serializeUrl(r) : r;
}

describe('guardas', () => {
  it('sinSesion deja pasar sin sesión y redirige con sesión', () => {
    expect(ejecutar(sinSesion, null)).toBe(true);
    expect(ejecutar(sinSesion, USUARIOS_SIMULADOS.cliente)).toBe('/cliente');
  });

  it('autenticado redirige a /acceso sin sesión', () => {
    expect(ejecutar(autenticado, null)).toBe('/acceso');
    expect(ejecutar(autenticado, USUARIOS_SIMULADOS.soporte)).toBe(true);
  });

  it('esCliente rechaza a un empleado', () => {
    expect(ejecutar(esCliente, USUARIOS_SIMULADOS.cliente)).toBe(true);
    expect(ejecutar(esCliente, USUARIOS_SIMULADOS.gestion)).toBe('/no-autorizado');
  });

  it('identidadPendiente solo acepta identidades sin registrar', () => {
    expect(ejecutar(identidadPendiente, USUARIOS_SIMULADOS.pendiente)).toBe(true);
    expect(ejecutar(identidadPendiente, USUARIOS_SIMULADOS.cliente)).toBe('/cliente');
  });

  it('operacion exige la operación en la sesión', () => {
    const g = operacion('MIGRAR_DATOS');
    expect(ejecutar(g, USUARIOS_SIMULADOS.admin)).toBe(true);
    expect(ejecutar(g, USUARIOS_SIMULADOS.gestion)).toBe('/no-autorizado');
  });
});
