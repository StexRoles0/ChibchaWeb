import { TestBed } from '@angular/core/testing';
import {
  ActivatedRoute,
  convertToParamMap,
  provideRouter,
  Router,
  UrlSegment,
} from '@angular/router';
import { of, throwError } from 'rxjs';
import { ClientesApi } from '../../core/api/clientes.api';
import { DetalleDTO, ResumenDTO } from '../../core/api/dto';
import { SoporteApi } from '../../core/api/soporte.api';
import { USUARIOS_SIMULADOS } from '../../core/api/simulado/sesiones';
import { SesionStore } from '../../core/auth/sesion.store';
import { hoyIso } from '../../shared/formato';
import { Bandeja } from './bandeja';
import { ReportarNovedad } from './reportar';
import { SOPORTE_ROUTES, bandejaMatcher } from './soporte.routes';
import { aTicket, nivelSiguiente } from './ticket';

const el = (f: { nativeElement: unknown }) => f.nativeElement as HTMLElement;
const escribir = (e: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement, v: string) => {
  e.value = v;
  e.dispatchEvent(new Event(e instanceof HTMLSelectElement ? 'change' : 'input'));
};
const boton = (raiz: HTMLElement, texto: string) =>
  Array.from(raiz.querySelectorAll<HTMLButtonElement>('button')).find((b) =>
    b.textContent?.includes(texto),
  )!;

const LISTA: ResumenDTO[] = [
  { id: 1042, titulo: 'RENDIMIENTO', subtitulo: 'Soporte', estado: 'ABIERTO' },
  { id: 1038, titulo: 'BASE_DATOS', subtitulo: 'Gestión', estado: 'ESCALADO' },
  { id: 1029, titulo: 'Otra', subtitulo: 'Desarrollo', estado: 'ESCALADO' },
];

const detalle = (id: number, estado: string, nivel: string, extra: string[] = []): DetalleDTO => ({
  id,
  titulo: `Ticket #${id}`,
  campos: [
    'categoria: RENDIMIENTO',
    `estado: ${estado}`,
    `nivel: ${nivel}`,
    'reportante: Steven Navarro (cliente)',
    'sitio: cafedeboyaca.chibchaweb.com',
    'fechaCreacion: 2026-11-16T09:14:00-05:00',
    'descripcion: El sitio tarda más de 10 segundos en cargar.',
    ...extra,
  ],
});

describe('ticket.ts', () => {
  it('aTicket separa los movimientos repetidos y conserva "|" dentro de la observación', () => {
    const t = aTicket(
      detalle(5, 'ESCALADO', 'Gestión', [
        'movimiento: 2026-11-16 10:30|Ana Ruiz|ESCALADO|Gestión|Revisar a|b',
        'movimiento: 2026-11-16 11:00|Luis Pérez|ESCALADO|Desarrollo|Sigue',
      ]),
    );
    expect(t.estado).toBe('ESCALADO');
    expect(t.movimientos).toEqual([
      {
        fecha: '2026-11-16 10:30',
        responsable: 'Ana Ruiz',
        estado: 'ESCALADO',
        nivel: 'Gestión',
        observacion: 'Revisar a|b',
      },
      {
        fecha: '2026-11-16 11:00',
        responsable: 'Luis Pérez',
        estado: 'ESCALADO',
        nivel: 'Desarrollo',
        observacion: 'Sigue',
      },
    ]);
  });

  it('nivelSiguiente: Soporte → Gestión → Desarrollo → nada', () => {
    expect(nivelSiguiente('Soporte')).toBe('Gestión');
    expect(nivelSiguiente('Gestión')).toBe('Desarrollo');
    expect(nivelSiguiente('Desarrollo')).toBeNull();
    expect(nivelSiguiente('Otro')).toBeNull();
  });
});

describe('rutas de soporte (docs/ui.md)', () => {
  it('bandeja y detalle comparten un solo Route con la guarda ATENDER_TICKETS', () => {
    const r = SOPORTE_ROUTES.find((x) => x.matcher)!;
    expect(r.canActivate?.length).toBe(1);
    const seg = (...p: string[]) => p.map((x) => new UrlSegment(x, {}));
    expect(bandejaMatcher(seg('bandeja'))?.consumed.length).toBe(1);
    expect(bandejaMatcher(seg('tickets', '1042'))?.posParams?.['id'].path).toBe('1042');
    expect(bandejaMatcher(seg('tickets'))).toBeNull();
    expect(bandejaMatcher(seg('reportar'))).toBeNull();
    expect(SOPORTE_ROUTES.find((x) => x.path === 'reportar')?.canActivate?.length).toBe(1);
  });
});

describe('M-10 Reportar una novedad', () => {
  async function montar(
    usuario: typeof USUARIOS_SIMULADOS.cliente,
    soporte: Partial<SoporteApi>,
    clientes: Partial<ClientesApi> = {},
  ) {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: SoporteApi, useValue: soporte },
        { provide: ClientesApi, useValue: clientes },
      ],
    });
    TestBed.inject(SesionStore).establecer(usuario);
    const f = TestBed.createComponent(ReportarNovedad);
    await f.whenStable();
    return f;
  }
  const sitios = () =>
    of([{ id: 7, titulo: 'cafedeboyaca.chibchaweb.com', subtitulo: 'UNIX', estado: 'ACTIVO' }]);
  const enviar = async (f: Awaited<ReturnType<typeof montar>>) => {
    el(f).querySelector('form')!.dispatchEvent(new Event('submit'));
    await f.whenStable();
  };

  it('el cliente ve el selector de sitio con los sitios del contrato y la tabla Mis tickets', async () => {
    const f = await montar(USUARIOS_SIMULADOS.cliente, { mios: () => of(LISTA) }, { sitios });
    expect(el(f).textContent).toContain('Reportar una novedad');
    expect(el(f).querySelector('label[for="idSitio"]')?.textContent).toContain('opcional');
    expect(Array.from(el(f).querySelectorAll('#idSitio option')).map((o) => o.textContent)).toEqual(
      ['Ninguno en particular', 'cafedeboyaca.chibchaweb.com'],
    );
    expect(Array.from(el(f).querySelectorAll('tbody tr'))[0].textContent).toMatch(
      /#1042\s+Rendimiento\s+Soporte\s+Abierto/,
    );
  });

  it('un empleado no ve el selector de sitio ni consulta los sitios', async () => {
    const sitiosSpy = vi.fn(sitios);
    const f = await montar(
      USUARIOS_SIMULADOS.gestion,
      { mios: () => of([]) },
      { sitios: sitiosSpy },
    );
    expect(el(f).querySelector('#idSitio')).toBeNull();
    expect(sitiosSpy).not.toHaveBeenCalled();
    expect(el(f).textContent).toContain('Todavía no has reportado ninguna novedad.');
    expect(el(f).querySelector('.migas a')?.getAttribute('href')).toBe('/gestion');
  });

  it('exige la descripción, envía idSitio numérico, confirma y recarga la tabla', async () => {
    const crear = vi.fn(() => of({ id: 1043 }));
    const mios = vi.fn(() => of(LISTA));
    const f = await montar(USUARIOS_SIMULADOS.cliente, { crear, mios }, { sitios });
    await enviar(f);
    expect(el(f).querySelector('#descripcion-error')?.textContent).toContain('obligatorio');
    expect(crear).not.toHaveBeenCalled();
    escribir(el(f).querySelector<HTMLSelectElement>('#categoria')!, 'CORREO');
    escribir(el(f).querySelector<HTMLSelectElement>('#idSitio')!, '7');
    escribir(el(f).querySelector<HTMLTextAreaElement>('#descripcion')!, ' No llegan correos ');
    await enviar(f);
    expect(crear).toHaveBeenCalledWith({
      categoria: 'CORREO',
      descripcion: 'No llegan correos',
      idSitio: 7,
    });
    expect(mios).toHaveBeenCalledTimes(2);
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain('#1043');
  });

  it('sin sitio elegido no manda idSitio', async () => {
    const crear = vi.fn(() => of({ id: 1 }));
    const f = await montar(USUARIOS_SIMULADOS.cliente, { crear, mios: () => of([]) }, { sitios });
    escribir(el(f).querySelector<HTMLTextAreaElement>('#descripcion')!, 'Algo falla');
    await enviar(f);
    expect(crear).toHaveBeenCalledWith({ categoria: 'RENDIMIENTO', descripcion: 'Algo falla' });
  });

  it('422 REGLA_NEGOCIO con campo idSitio va bajo el selector de sitio', async () => {
    const f = await montar(
      USUARIOS_SIMULADOS.cliente,
      {
        mios: () => of([]),
        crear: () =>
          throwError(() => ({
            estado: 422,
            codigo: 'REGLA_NEGOCIO',
            campo: 'idSitio',
            mensaje: 'El sitio indicado no pertenece al cliente.',
          })),
      },
      { sitios },
    );
    escribir(el(f).querySelector<HTMLTextAreaElement>('#descripcion')!, 'Algo falla');
    await enviar(f);
    expect(el(f).querySelector('#idSitio-error')?.textContent).toContain('no pertenece');
  });

  it('si los sitios no cargan avisa y deja enviar sin sitio', async () => {
    const f = await montar(
      USUARIOS_SIMULADOS.cliente,
      { mios: () => of([]) },
      { sitios: () => throwError(() => ({ mensaje: 'x' })) },
    );
    expect(el(f).textContent).toContain('No pudimos cargar tus sitios');
  });
});

describe('M-17 Bandeja de tickets', () => {
  async function montar(
    soporte: Partial<SoporteApi>,
    id: string | null = null,
  ): Promise<{ f: ReturnType<typeof TestBed.createComponent<Bandeja>>; router: Router }> {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: SoporteApi, useValue: soporte },
        {
          provide: ActivatedRoute,
          useValue: { paramMap: of(convertToParamMap(id ? { id } : {})) },
        },
      ],
    });
    TestBed.inject(SesionStore).establecer(USUARIOS_SIMULADOS.soporte);
    const router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
    const f = TestBed.createComponent(Bandeja);
    await f.whenStable();
    return { f, router };
  }

  it('pide la bandeja de hoy y la lista con tipo, nivel y estado; sin selección invita a elegir', async () => {
    const diarios = vi.fn(() => of(LISTA));
    const { f } = await montar({ diarios });
    expect(diarios).toHaveBeenCalledWith(hoyIso());
    expect(el(f).textContent).toContain('Tickets del día');
    expect(el(f).textContent).toContain('Creados hoy y abiertos de días anteriores');
    const filas = Array.from(el(f).querySelectorAll('tbody tr'));
    expect(filas.length).toBe(3);
    expect(filas[1].textContent).toMatch(/#1038.*Base de datos.*Gestión.*Escalado/);
    expect(el(f).textContent).toContain('Selecciona un ticket');
  });

  it('lista vacía y error de carga con Reintentar', async () => {
    const { f } = await montar({ diarios: () => of([]) });
    expect(el(f).textContent).toContain('No hay tickets para esta fecha.');
    let falla = true;
    const { f: g } = await montar({
      diarios: () => (falla ? throwError(() => ({ mensaje: 'Sin conexión.' })) : of(LISTA)),
    });
    expect(el(g).querySelector('.aviso.error')?.textContent).toContain('Sin conexión.');
    falla = false;
    boton(el(g), 'Reintentar').click();
    await g.whenStable();
    expect(el(g).querySelectorAll('tbody tr').length).toBe(3);
  });

  it('cambiar la fecha vuelve a pedir la bandeja de ese día', async () => {
    const diarios = vi.fn(() => of(LISTA));
    const { f } = await montar({ diarios });
    escribir(el(f).querySelector<HTMLInputElement>('#fecha')!, '2026-11-01');
    await f.whenStable();
    expect(diarios).toHaveBeenLastCalledWith('2026-11-01');
    expect(el(f).textContent).toContain('domingo 1 de noviembre de 2026');
  });

  it('elegir una fila navega a /soporte/tickets/:id', async () => {
    const { f, router } = await montar({ diarios: () => of(LISTA) });
    (el(f).querySelectorAll('tbody tr')[1] as HTMLElement).click();
    expect(router.navigate).toHaveBeenCalledWith(['/soporte/tickets', 1038]);
  });

  it('con :id carga el detalle: datos, movimientos, observación y botón con el nivel siguiente', async () => {
    const d = detalle(1042, 'ABIERTO', 'Soporte');
    const { f } = await montar({ diarios: () => of(LISTA), detalle: () => of(d) }, '1042');
    const t = el(f).textContent!;
    expect(t).toContain('Ticket #1042');
    expect(t).toContain('Abierto · Nivel Soporte');
    expect(t).toContain('Steven Navarro (cliente)');
    expect(t).toContain('cafedeboyaca.chibchaweb.com');
    expect(t).toContain('Aún no tiene movimientos.');
    expect(el(f).querySelector('label[for="observacion"]')?.textContent).toContain('Observación');
    expect(boton(el(f), 'Escalar a Gestión').disabled).toBe(false);
    expect(boton(el(f), 'Marcar resuelto').disabled).toBe(false);
    expect(el(f).querySelector('tr.seleccionada')?.textContent).toContain('#1042');
  });

  it('en el último nivel Escalar queda deshabilitado y se explica por qué', async () => {
    const d = detalle(1029, 'ESCALADO', 'Desarrollo', [
      'movimiento: 2026-11-15 09:10|Gabriela Gestión|ESCALADO|Desarrollo|Caché saturada',
    ]);
    const { f } = await montar({ diarios: () => of(LISTA), detalle: () => of(d) }, '1029');
    expect(boton(el(f), 'Escalar de nivel').disabled).toBe(true);
    expect(boton(el(f), 'Marcar resuelto').disabled).toBe(false);
    expect(el(f).textContent).toContain('último nivel de servicio');
    expect(el(f).querySelector('.movimientos')?.textContent).toContain('Caché saturada');
  });

  it('un ticket resuelto no ofrece acciones', async () => {
    const d = detalle(1020, 'RESUELTO', 'Soporte');
    const { f } = await montar({ diarios: () => of(LISTA), detalle: () => of(d) }, '1020');
    expect(el(f).textContent).toContain('ya está resuelto');
    expect(el(f).querySelector('#observacion')).toBeNull();
    expect(boton(el(f), 'Escalar')).toBeUndefined();
  });

  it('la observación es obligatoria: sin ella no se llama al servicio', async () => {
    const enrutar = vi.fn(() => of(undefined));
    const d = detalle(1042, 'ABIERTO', 'Soporte');
    const { f } = await montar({ diarios: () => of(LISTA), detalle: () => of(d), enrutar }, '1042');
    boton(el(f), 'Escalar a Gestión').click();
    await f.whenStable();
    expect(el(f).querySelector('#observacion-error')?.textContent).toContain('obligatorio');
    expect(enrutar).not.toHaveBeenCalled();
  });

  it('Escalar manda escalar=true con la observación y refresca detalle y lista', async () => {
    const enrutar = vi.fn(() => of(undefined));
    const diarios = vi.fn(() => of(LISTA));
    const detalleFn = vi
      .fn()
      .mockReturnValueOnce(of(detalle(1042, 'ABIERTO', 'Soporte')))
      .mockReturnValue(of(detalle(1042, 'ESCALADO', 'Gestión')));
    const { f } = await montar({ diarios, detalle: detalleFn, enrutar }, '1042');
    escribir(el(f).querySelector<HTMLTextAreaElement>('#observacion')!, ' Revisar caché ');
    boton(el(f), 'Escalar a Gestión').click();
    await f.whenStable();
    await f.whenStable();
    expect(enrutar).toHaveBeenCalledWith(1042, { escalar: true, observacion: 'Revisar caché' });
    expect(diarios).toHaveBeenCalledTimes(2);
    expect(detalleFn).toHaveBeenCalledTimes(2);
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain('escalado a Gestión');
    expect(el(f).textContent).toContain('Escalado · Nivel Gestión');
  });

  it('Marcar resuelto manda escalar=false', async () => {
    const enrutar = vi.fn(() => of(undefined));
    const d = detalle(1042, 'ABIERTO', 'Soporte');
    const { f } = await montar({ diarios: () => of(LISTA), detalle: () => of(d), enrutar }, '1042');
    escribir(el(f).querySelector<HTMLTextAreaElement>('#observacion')!, 'Resuelto con reinicio');
    boton(el(f), 'Marcar resuelto').click();
    await f.whenStable();
    expect(enrutar).toHaveBeenCalledWith(1042, {
      escalar: false,
      observacion: 'Resuelto con reinicio',
    });
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain('marcado como resuelto');
  });

  it('409 ESTADO_INVALIDO: muestra el mensaje y vuelve a leer el ticket para ver su estado real', async () => {
    const enrutar = vi.fn(() =>
      throwError(() => ({
        estado: 409,
        codigo: 'ESTADO_INVALIDO',
        mensaje: 'El ticket ya está resuelto.',
      })),
    );
    const detalleFn = vi
      .fn()
      .mockReturnValueOnce(of(detalle(1042, 'ABIERTO', 'Soporte')))
      .mockReturnValue(of(detalle(1042, 'RESUELTO', 'Soporte')));
    const { f } = await montar({ diarios: () => of(LISTA), detalle: detalleFn, enrutar }, '1042');
    escribir(el(f).querySelector<HTMLTextAreaElement>('#observacion')!, 'Escalar');
    boton(el(f), 'Escalar a Gestión').click();
    await f.whenStable();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('ya está resuelto');
    expect(el(f).textContent).toContain('Resuelto · Nivel Soporte');
    expect(el(f).querySelector('#observacion')).toBeNull();
  });

  it('422 de observación va bajo el campo y 404 del detalle muestra el aviso', async () => {
    const d = detalle(1042, 'ABIERTO', 'Soporte');
    const { f } = await montar(
      {
        diarios: () => of(LISTA),
        detalle: () => of(d),
        enrutar: () =>
          throwError(() => ({
            estado: 422,
            codigo: 'VALIDACION',
            campo: 'observacion',
            mensaje: 'La observación es obligatoria.',
          })),
      },
      '1042',
    );
    escribir(el(f).querySelector<HTMLTextAreaElement>('#observacion')!, 'x');
    boton(el(f), 'Marcar resuelto').click();
    await f.whenStable();
    expect(el(f).querySelector('#observacion-error')?.textContent).toContain('obligatoria');

    const { f: g } = await montar(
      {
        diarios: () => of(LISTA),
        detalle: () =>
          throwError(() => ({
            estado: 404,
            codigo: 'NO_ENCONTRADO',
            mensaje: 'El ticket no existe.',
          })),
      },
      '9',
    );
    expect(el(g).querySelector('.aviso.error')?.textContent).toContain('El ticket no existe.');
  });
});
