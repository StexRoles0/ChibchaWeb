import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { ClientesApi } from '../../core/api/clientes.api';
import { AccesoApi } from '../../core/api/acceso.api';
import { DetalleDTO } from '../../core/api/dto';
import { USUARIOS_SIMULADOS } from '../../core/api/simulado/sesiones';
import { SesionStore } from '../../core/auth/sesion.store';
import { EditarPerfil, nombreCortoDeSitio } from './editar';
import { InicioCliente } from './inicio';
import { aPerfil, PerfilStore } from './perfil.store';
import { Perfil } from './perfil';
import { camposDeDetalle, fechaCorta } from '../../shared/formato';

const DETALLE: DetalleDTO = {
  id: 1,
  titulo: 'Steven Navarro Parrales',
  campos: [
    'nombre: Steven Navarro Parrales',
    'correo: steven@correo.co',
    'telefono: 300 412 5587',
    'lineaResidencia: Calle 24 # 7-31',
    'ciudadResidencia: Sogamoso',
    'codigoPostalResidencia: 152210',
    'lineaFacturacion: Calle 24 # 7-31',
    'ciudadFacturacion: Sogamoso',
    'codigoPostalFacturacion: 152210',
    'tarjeta: VISA •••• 1111',
    'franquicia: VISA',
    'vencimiento: 2028-08-01',
    'idSuscripcion: 7',
    'sitio: cafedeboyaca.chibchaweb.com',
    'plataforma: UNIX',
    'idPaquete: 3',
    'paquete: Chibcha-Platino',
    'idPlan: 4',
    'plan: Anual',
    'montoPeriodo: 204.00',
    'fechaCorte: 2027-09-14',
    'distribuidor: ',
    'activo: true',
  ],
};
const CAT = {
  paquetes: () => of([{ id: 3, titulo: 'Chibcha-Platino', subtitulo: '20.00', estado: 'ACTIVO' }]),
  planes: () => of([{ id: 4, titulo: 'Anual', subtitulo: '12|0.15', estado: 'ACTIVO' }]),
};

function montar(clientes: Partial<ClientesApi>, extra: Record<string, unknown>[] = []) {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      PerfilStore,
      { provide: ClientesApi, useValue: clientes },
      { provide: AccesoApi, useValue: { ...CAT, sesion: () => of(USUARIOS_SIMULADOS.cliente!) } },
      ...(extra as never[]),
    ],
  });
  TestBed.inject(SesionStore).establecer(USUARIOS_SIMULADOS.cliente);
}

describe('formato y DetalleDTO', () => {
  it('parsea "clave: valor" y conserva los dos puntos del valor', () => {
    const c = camposDeDetalle({ id: 1, titulo: 't', campos: ['a: 1', 'hora: 10:30', 'vacio: '] });
    expect(c).toEqual({ a: '1', hora: '10:30', vacio: '' });
    expect(fechaCorta('2027-09-14')).toBe('14 sep 2027');
    expect(nombreCortoDeSitio('cafedeboyaca.chibchaweb.com')).toBe('cafedeboyaca');
    expect(nombreCortoDeSitio('cafe')).toBe('cafe');
  });

  it('aPerfil tipa ids y activo', () => {
    const p = aPerfil(camposDeDetalle(DETALLE));
    expect(p).toMatchObject({
      idSuscripcion: 7,
      idPaquete: 3,
      idPlan: 4,
      activo: true,
      distribuidor: '',
    });
  });
});

describe('M-05 Inicio del cliente', () => {
  it('sale de GET /clientes/me: sitio, paquete y plan con monto, próximo cobro y tarjeta', async () => {
    montar({ detalle: () => of(DETALLE) });
    const f = TestBed.createComponent(InicioCliente);
    await f.whenStable();
    const t = (f.nativeElement as HTMLElement).textContent!;
    expect(t).toContain('Hola, Steven');
    expect(t).toContain('cafedeboyaca.chibchaweb.com');
    expect(t).toContain('Activo');
    expect(t).toContain('Plan anual · US$ 204.00');
    expect(t).toContain('14 sep 2027');
    expect(t).toContain('VISA •••• 1111');
  });

  it('si falla muestra el error con Reintentar', async () => {
    montar({ detalle: () => throwError(() => ({ estado: 500, mensaje: 'Falló' })) });
    const f = TestBed.createComponent(InicioCliente);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('.aviso.error')?.textContent).toContain('Falló');
    expect(el.textContent).toContain('Reintentar');
  });
});

describe('M-06 Perfil y M-08 Eliminar', () => {
  it('M-06 muestra datos personales, hospedaje y las dos acciones', async () => {
    montar({ detalle: () => of(DETALLE) });
    const f = TestBed.createComponent(Perfil);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    const t = el.textContent!;
    expect(t).toContain('Calle 24 # 7-31, Sogamoso');
    expect(t).toContain('Sin distribuidor');
    expect(t).toContain('Unix');
    expect(t).toContain('VISA •••• 1111 · vence 08/28');
    expect(el.querySelector('a[href="/cliente/perfil/editar"]')).not.toBeNull();
    expect(el.querySelector('a[href="/cliente/perfil/eliminar"]')).not.toBeNull();
    expect(el.querySelector('[role="dialog"]')).toBeNull();
  });

  it('M-08: el botón se habilita solo con el correo correcto y elimina (204) → /acceso', async () => {
    const eliminar = vi.fn(() => of(undefined));
    montar({ detalle: () => of(DETALLE), eliminar });
    const router = TestBed.inject(Router);
    vi.spyOn(router, 'url', 'get').mockReturnValue('/cliente/perfil/eliminar');
    const nav = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
    const f = TestBed.createComponent(Perfil);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    expect(el.querySelector('[role="dialog"]')).not.toBeNull();
    const confirmar = () =>
      Array.from(el.querySelectorAll<HTMLButtonElement>('[role="dialog"] button')).find((b) =>
        b.textContent?.includes('Eliminar mi cuenta'),
      )!;
    expect(confirmar().disabled).toBe(true);

    const input = el.querySelector<HTMLInputElement>('#correo-confirmacion')!;
    input.value = 'otro@correo.co';
    input.dispatchEvent(new Event('input'));
    await f.whenStable();
    expect(confirmar().disabled).toBe(true);

    input.value = 'Steven@Correo.co';
    input.dispatchEvent(new Event('input'));
    await f.whenStable();
    expect(confirmar().disabled).toBe(false);

    confirmar().click();
    await f.whenStable();
    expect(eliminar).toHaveBeenCalledOnce();
    expect(TestBed.inject(SesionStore).sesion()).toBeNull();
    expect(nav).toHaveBeenCalledWith('/acceso');
  });

  it('M-08: si el servidor rechaza, el error queda dentro del diálogo y la sesión sigue', async () => {
    montar({
      detalle: () => of(DETALLE),
      eliminar: () =>
        throwError(() => ({ estado: 409, codigo: 'ESTADO_INVALIDO', mensaje: 'Ya está inactivo' })),
    });
    vi.spyOn(TestBed.inject(Router), 'url', 'get').mockReturnValue('/cliente/perfil/eliminar');
    const f = TestBed.createComponent(Perfil);
    await f.whenStable();
    const el = f.nativeElement as HTMLElement;
    const input = el.querySelector<HTMLInputElement>('#correo-confirmacion')!;
    input.value = 'steven@correo.co';
    input.dispatchEvent(new Event('input'));
    await f.whenStable();
    Array.from(el.querySelectorAll<HTMLButtonElement>('[role="dialog"] button'))
      .find((b) => b.textContent?.includes('Eliminar mi cuenta'))!
      .click();
    await f.whenStable();
    expect(el.querySelector('[role="dialog"] .aviso.error')?.textContent).toContain(
      'Ya está inactivo',
    );
    expect(TestBed.inject(SesionStore).esCliente()).toBe(true);
  });
});

const asentar = async (f: { detectChanges(): void; whenStable(): Promise<unknown> }) => {
  f.detectChanges();
  await new Promise((r) => setTimeout(r));
  await f.whenStable();
};

describe('M-07 Modificar perfil', () => {
  function editar(pestana: string | null, clientes: Partial<ClientesApi>) {
    const params = new BehaviorSubject(convertToParamMap(pestana ? { pestana } : {}));
    montar(clientes, [
      {
        provide: ActivatedRoute,
        useValue: { queryParamMap: params, snapshot: { queryParamMap: params.value } },
      },
    ]);
    const f = TestBed.createComponent(EditarPerfil);
    return { f, el: f.nativeElement as HTMLElement };
  }
  const guardar = (el: HTMLElement) =>
    Array.from(el.querySelectorAll<HTMLButtonElement>('button')).find((b) =>
      b.textContent?.includes('Guardar'),
    )!;
  const escribir = (el: HTMLElement, id: string, valor: string) => {
    const i = el.querySelector<HTMLInputElement>(`#${id}`)!;
    i.value = valor;
    i.dispatchEvent(new Event('input'));
  };

  it('PERSONAL: precarga, bloquea el correo y manda solo el bloque personal', async () => {
    const modificar = vi.fn(() => of(undefined));
    const { f, el } = editar(null, { detalle: () => of(DETALLE), modificar });
    await asentar(f);
    expect(el.querySelectorAll('[role="tab"]')).toHaveLength(3);
    expect(el.querySelector('#pestana-PERSONAL')?.getAttribute('aria-selected')).toBe('true');
    expect(el.querySelector<HTMLInputElement>('#correo')!.readOnly).toBe(true);
    expect(el.querySelector<HTMLInputElement>('#sitio')!.value).toBe('cafedeboyaca');

    escribir(el, 'telefono', '310 555 0198');
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(modificar).toHaveBeenCalledOnce();
    const [categoria, cuerpo] = modificar.mock.calls[0] as unknown as [
      string,
      Record<string, unknown>,
    ];
    expect(categoria).toBe('PERSONAL');
    expect(Object.keys(cuerpo).sort()).toEqual([
      'ciudadResidencia',
      'codigoPostalResidencia',
      'lineaResidencia',
      'nombre',
      'plataforma',
      'sitio',
      'telefono',
    ]);
    expect(cuerpo['telefono']).toBe('310 555 0198');
    expect(el.querySelector('.aviso.exito')?.textContent).toContain('Cambios guardados');
  });

  it('PERSONAL: un 422 con campo se muestra debajo de ese campo', async () => {
    const { f, el } = editar(null, {
      detalle: () => of(DETALLE),
      modificar: () =>
        throwError(() => ({
          estado: 422,
          codigo: 'VALIDACION',
          mensaje: 'Teléfono inválido',
          campo: 'telefono',
        })),
    });
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(el.querySelector('#telefono-error')?.textContent).toContain('Teléfono inválido');
  });

  it('PERSONAL: subdominio en uso (409) queda bajo el campo del sitio', async () => {
    const { f, el } = editar(null, {
      detalle: () => of(DETALLE),
      modificar: () =>
        throwError(() => ({ estado: 409, codigo: 'SUBDOMINIO_EN_USO', mensaje: 'Ya está en uso' })),
    });
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(el.querySelector('#sitio-error')?.textContent).toContain('Ya está en uso');
  });

  it('PAQUETE_PLAN: manda idSuscripcion, idPaquete e idPlan, y avisa que aplica al próximo corte', async () => {
    const modificar = vi.fn(() => of(undefined));
    const { f, el } = editar('PAQUETE_PLAN', { detalle: () => of(DETALLE), modificar });
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(modificar).toHaveBeenCalledWith('PAQUETE_PLAN', {
      idSuscripcion: 7,
      idPaquete: 3,
      idPlan: 4,
    });
    expect(el.querySelector('.aviso.exito')?.textContent).toContain('próximo corte');
  });

  it('PAGO: no envía con formulario inválido; con datos válidos manda el bloque de pago', async () => {
    const modificar = vi.fn(() => of(undefined));
    const { f, el } = editar('PAGO', { detalle: () => of(DETALLE), modificar });
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(modificar).not.toHaveBeenCalled();
    expect(el.querySelector('#numeroTarjeta-error')?.textContent).toContain('obligatorio');

    escribir(el, 'numeroTarjeta', '4111111111111111');
    escribir(el, 'vencimiento', '0830');
    escribir(el, 'codigoSeguridad', '123');
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(modificar).toHaveBeenCalledWith('PAGO', {
      lineaFacturacion: 'Calle 24 # 7-31',
      ciudadFacturacion: 'Sogamoso',
      codigoPostalFacturacion: '152210',
      numeroTarjeta: '4111111111111111',
      vencimiento: '2030-08-01',
      codigoSeguridad: '123',
      franquicia: 'VISA',
    });
  });

  it('PAGO: tarjeta rechazada (422) queda bajo el número', async () => {
    const { f, el } = editar('PAGO', {
      detalle: () => of(DETALLE),
      modificar: () =>
        throwError(() => ({
          estado: 422,
          codigo: 'VALIDACION',
          mensaje: 'La tarjeta fue rechazada por el verificador.',
          campo: 'numeroTarjeta',
        })),
    });
    await asentar(f);
    escribir(el, 'numeroTarjeta', '4111111111110002');
    escribir(el, 'vencimiento', '0830');
    escribir(el, 'codigoSeguridad', '123');
    await asentar(f);
    guardar(el).click();
    await asentar(f);
    expect(el.querySelector('#numeroTarjeta-error')?.textContent).toContain('rechazada');
  });
});
