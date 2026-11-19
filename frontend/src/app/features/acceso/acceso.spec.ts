import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AccesoApi } from '../../core/api/acceso.api';
import { USUARIOS_SIMULADOS } from '../../core/api/simulado/sesiones';
import { SesionStore } from '../../core/auth/sesion.store';
import { Navegador } from '../../core/navegador';
import { Acceso } from './acceso';
import { Callback } from './callback';

describe('M-01 Acceso', () => {
  function crear(api: Partial<AccesoApi>) {
    const ir = vi.fn();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AccesoApi, useValue: api },
        { provide: Navegador, useValue: { ir } },
      ],
    });
    const f = TestBed.createComponent(Acceso);
    return { f, ir, el: f.nativeElement as HTMLElement };
  }
  const botones = (el: HTMLElement) =>
    Array.from(el.querySelectorAll<HTMLButtonElement>('button.opcion'));

  it('en desarrollo exige el correo de prueba antes de pedir la URL (AUTH-01)', async () => {
    const oauthInicio = vi.fn(() => of({ url: '/x' }));
    const { f, el, ir } = crear({ oauthInicio });
    await f.whenStable();
    botones(el)[0].click();
    await f.whenStable();
    expect(oauthInicio).not.toHaveBeenCalled();
    expect(ir).not.toHaveBeenCalled();
    expect(el.querySelector('#correo-prueba-error')?.textContent).toContain('correo de prueba');
  });

  it('manda el correo de prueba y redirige a la URL recibida; "Crear una cuenta" hace lo mismo', async () => {
    const oauthInicio = vi.fn(() => of({ url: '/auth/callback?code=dev:a@b.co&state=s' }));
    const { f, el, ir } = crear({ oauthInicio });
    await f.whenStable();
    const input = el.querySelector<HTMLInputElement>('#correo-prueba')!;
    input.value = 'a@b.co';
    input.dispatchEvent(new Event('input'));
    botones(el)[1].click();
    await f.whenStable();
    expect(oauthInicio).toHaveBeenCalledWith('a@b.co');
    expect(ir).toHaveBeenCalledWith('/auth/callback?code=dev:a@b.co&state=s');
    expect(botones(el)[0].textContent).toContain('Redirigiendo…');
  });

  it('muestra el error si el inicio falla', async () => {
    const { f, el } = crear({
      oauthInicio: () =>
        throwError(() => ({
          estado: 400,
          codigo: 'SOLICITUD_INVALIDA',
          mensaje: 'Falta el correo',
        })),
    });
    await f.whenStable();
    const input = el.querySelector<HTMLInputElement>('#correo-prueba')!;
    input.value = 'a@b.co';
    input.dispatchEvent(new Event('input'));
    botones(el)[0].click();
    await f.whenStable();
    expect(el.querySelector('.aviso.error')?.textContent).toContain('Falta el correo');
  });
});

describe('/auth/callback', () => {
  function crear(query: Record<string, string>, api: Partial<AccesoApi>) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AccesoApi, useValue: api },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(query) } },
        },
      ],
    });
    const nav = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    return { nav, sesion: TestBed.inject(SesionStore) };
  }

  it('manda code y state, guarda la sesión y redirige según el rol (cliente → /cliente)', async () => {
    const callback = vi.fn(() => of(USUARIOS_SIMULADOS.cliente!));
    const { nav, sesion } = crear({ code: 'dev:x', state: 's1' }, { callback });
    await TestBed.createComponent(Callback).componentInstance.ngOnInit();
    expect(callback).toHaveBeenCalledWith({ codigo: 'dev:x', estado: 's1' });
    expect(sesion.esCliente()).toBe(true);
    expect(nav).toHaveBeenCalledWith('/cliente', { replaceUrl: true });
  });

  it('identidad sin registrar → /registro/datos (AUTH-02 FA2)', async () => {
    const { nav } = crear(
      { code: 'dev:n', state: 's' },
      { callback: () => of(USUARIOS_SIMULADOS.pendiente!) },
    );
    await TestBed.createComponent(Callback).componentInstance.ngOnInit();
    expect(nav).toHaveBeenCalledWith('/registro/datos', { replaceUrl: true });
  });

  it('empleado de soporte → /soporte/bandeja', async () => {
    const { nav } = crear(
      { code: 'c', state: 's' },
      { callback: () => of(USUARIOS_SIMULADOS.soporte!) },
    );
    await TestBed.createComponent(Callback).componentInstance.ngOnInit();
    expect(nav).toHaveBeenCalledWith('/soporte/bandeja', { replaceUrl: true });
  });

  it('401 AUTORIZACION_FALLIDA o 403 USUARIO_INACTIVO → vuelve a M-01 con el mensaje', async () => {
    const { nav } = crear(
      { code: 'c', state: 's' },
      {
        callback: () =>
          throwError(() => ({
            estado: 403,
            codigo: 'USUARIO_INACTIVO',
            mensaje: 'Tu cuenta está dada de baja.',
          })),
      },
    );
    await TestBed.createComponent(Callback).componentInstance.ngOnInit();
    expect(nav).toHaveBeenCalledWith('/acceso', {
      replaceUrl: true,
      state: { error: 'Tu cuenta está dada de baja.' },
    });
  });

  it('sin code o state no llama a la API y vuelve a M-01', async () => {
    const callback = vi.fn();
    const { nav } = crear({ code: 'c' }, { callback });
    await TestBed.createComponent(Callback).componentInstance.ngOnInit();
    expect(callback).not.toHaveBeenCalled();
    expect(nav).toHaveBeenCalledWith('/acceso', expect.objectContaining({ replaceUrl: true }));
  });
});
