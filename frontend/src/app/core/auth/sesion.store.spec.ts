import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AccesoApi } from '../api/acceso.api';
import { USUARIOS_SIMULADOS } from '../api/simulado/sesiones';
import { SesionStore } from './sesion.store';

function crear(sesion: ReturnType<AccesoApi['sesion']>) {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([{ path: 'acceso', children: [] }]),
      { provide: AccesoApi, useValue: { sesion: () => sesion, logout: () => of(undefined) } },
    ],
  });
  return TestBed.inject(SesionStore);
}

describe('SesionStore', () => {
  it('carga la sesión y calcula la ruta de inicio por rol', async () => {
    const store = crear(of(USUARIOS_SIMULADOS.admin!));
    await store.cargar();
    expect(store.autenticada()).toBe(true);
    expect(store.rutaInicio()).toBe('/admin');
    expect(store.tieneOperacion('MIGRAR_DATOS')).toBe(true);
  });

  it('manda a registro cuando la identidad no está registrada', async () => {
    const store = crear(of(USUARIOS_SIMULADOS.pendiente!));
    await store.cargar();
    expect(store.identidadPendiente()).toBe(true);
    expect(store.rutaInicio()).toBe('/registro/datos');
  });

  it('deja la sesión vacía si el servidor responde 401', async () => {
    const store = crear(throwError(() => ({ estado: 401 })));
    await store.cargar();
    expect(store.sesion()).toBeNull();
    expect(store.cargada()).toBe(true);
    expect(store.rutaInicio()).toBe('/acceso');
  });

  it('cierra la sesión', async () => {
    const store = crear(of(USUARIOS_SIMULADOS.cliente!));
    await store.cargar();
    await store.cerrarSesion();
    expect(store.sesion()).toBeNull();
  });
});
