import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ConsultasApi } from '../../core/api/consultas.api';
import { DistribuidoresApi } from '../../core/api/distribuidores.api';
import { DetalleDTO, ResumenDTO } from '../../core/api/dto';
import { EmpleadosApi } from '../../core/api/empleados.api';
import { USUARIOS_SIMULADOS } from '../../core/api/simulado/sesiones';
import { SesionStore } from '../../core/auth/sesion.store';
import { ClientesGestion } from './clientes';
import { DetallePersonal } from './detalle';
import { FormularioPersonal } from './formulario';
import { InicioGestion } from './inicio';
import { ListadoPersonal } from './listado';
import { GESTION_ROUTES } from './gestion.routes';

const FILAS: ResumenDTO[] = [
  { id: 1, titulo: 'Ana Gómez', subtitulo: '1001 · Soporte', estado: 'ACTIVO' },
  { id: 2, titulo: 'Sara Díaz', subtitulo: '1003 · Soporte', estado: 'INACTIVO' },
];
const ROLES: ResumenDTO[] = [
  { id: 1, titulo: 'Gestión', subtitulo: '', estado: 'ACTIVO' },
  { id: 2, titulo: 'Soporte', subtitulo: '', estado: 'ACTIVO' },
];
const DET_EMP: DetalleDTO = {
  id: 7,
  titulo: 'Jorge Suárez Ramírez',
  campos: [
    'nombre: Jorge Suárez Ramírez',
    'documento: 1000000007',
    'correo: jorge@chibchaweb.com',
    'telefono: 311 222 3344',
    'idRol: 2',
    'rol: Soporte',
    'activo: true',
    'fechaRegistro: 2026-03-02',
  ],
};
const DET_DIS: DetalleDTO = {
  id: 10,
  titulo: 'Andes Digital SAS',
  campos: [
    'nombre: Andes Digital SAS',
    'documento: 900123456',
    'correo: contacto@andesdigital.co',
    'telefono: 6015556677',
    'codigo: DIS-ANDES1',
    'categoria: Premium',
    'referidos: 128',
    'activo: true',
  ],
};

const el = (f: { nativeElement: unknown }) => f.nativeElement as HTMLElement;
const esperar = (ms = 0) => new Promise((r) => setTimeout(r, ms));
const escribir = (input: HTMLInputElement | HTMLSelectElement, valor: string) => {
  input.value = valor;
  input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? 'change' : 'input'));
};
const boton = (raiz: HTMLElement, texto: string) =>
  Array.from(raiz.querySelectorAll<HTMLButtonElement>('button')).find((b) =>
    b.textContent?.includes(texto),
  )!;

function montar(
  datos: { tipo?: string } | null,
  apis: {
    emp?: Partial<EmpleadosApi>;
    dis?: Partial<DistribuidoresApi>;
    con?: Partial<ConsultasApi>;
  } = {},
  params: Record<string, string> = {},
  usuario = USUARIOS_SIMULADOS.gestion,
) {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: EmpleadosApi, useValue: apis.emp ?? {} },
      { provide: DistribuidoresApi, useValue: apis.dis ?? {} },
      { provide: ConsultasApi, useValue: apis.con ?? {} },
      {
        provide: ActivatedRoute,
        useValue: { snapshot: { data: datos ?? {}, paramMap: convertToParamMap(params) } },
      },
    ],
  });
  TestBed.inject(SesionStore).establecer(usuario);
}

describe('rutas de gestión (docs/ui.md)', () => {
  const ruta = (p: string) => GESTION_ROUTES.find((r) => r.path === p)!;
  const guardas = (p: string) => ruta(p).canActivate?.length ?? 0;

  it('todas las rutas M-11 a M-16 tienen guarda y distribuidores usa su propia operación', () => {
    for (const r of GESTION_ROUTES) expect(r.canActivate?.length).toBe(1);
    expect(guardas('distribuidores')).toBe(1);
    expect(ruta('empleados/nuevo').path).toBe('empleados/nuevo');
    const paths = GESTION_ROUTES.map((r) => r.path);
    expect(paths.indexOf('empleados/nuevo')).toBeLessThan(paths.indexOf('empleados/:id'));
    expect(paths.indexOf('distribuidores/nuevo')).toBeLessThan(paths.indexOf('distribuidores/:id'));
  });
});

describe('M-11 Inicio de gestión', () => {
  it('cuenta los activos de cada listado y enlaza las tres secciones', async () => {
    montar(null, {
      emp: { listar: () => of(FILAS) },
      dis: { listar: () => of([...FILAS, { ...FILAS[0], id: 3 }]) },
      con: { basico: () => of([FILAS[0]]) },
    });
    const f = TestBed.createComponent(InicioGestion);
    await f.whenStable();
    const t = el(f).textContent!;
    expect(t).toContain('Panel de gestión');
    const cifras = Array.from(el(f).querySelectorAll('.cifra')).map((c) => c.textContent!.trim());
    expect(cifras).toEqual(['1', '2', '1']);
    expect(el(f).querySelector('a[href="/gestion/distribuidores"]')).not.toBeNull();
    expect(el(f).querySelector('a[href="/gestion/clientes"]')).not.toBeNull();
  });

  it('si un listado falla, esa tarjeta muestra un guion y las demás siguen', async () => {
    montar(null, {
      emp: { listar: () => throwError(() => ({ estado: 500, mensaje: 'x' })) },
      dis: { listar: () => of(FILAS) },
      con: { basico: () => of(FILAS) },
    });
    const f = TestBed.createComponent(InicioGestion);
    await f.whenStable();
    expect(Array.from(el(f).querySelectorAll('.cifra')).map((c) => c.textContent!.trim())).toEqual([
      '—',
      '1',
      '1',
    ]);
  });

  it('no consulta ni muestra lo que la sesión no puede usar', async () => {
    const listar = vi.fn(() => of(FILAS));
    montar(
      null,
      { emp: { listar }, dis: { listar }, con: { basico: listar } },
      {},
      { ...USUARIOS_SIMULADOS.gestion!, operaciones: ['GESTIONAR_EMPLEADOS'] },
    );
    const f = TestBed.createComponent(InicioGestion);
    await f.whenStable();
    expect(listar).toHaveBeenCalledTimes(1);
    expect(el(f).querySelectorAll('.cifra').length).toBe(1);
  });
});

describe('M-12 Empleados / M-15 Distribuidores', () => {
  it('lista con estado en texto, acciones Ver · Editar · Eliminar y conteo', async () => {
    montar({ tipo: 'empleado' }, { emp: { listar: () => of(FILAS) } });
    const f = TestBed.createComponent(ListadoPersonal);
    await f.whenStable();
    const t = el(f).textContent!;
    expect(t).toContain('Ana Gómez');
    expect(t).toContain('Mostrando 2 registros');
    expect(el(f).querySelector('a[href="/gestion/empleados/nuevo"]')?.textContent).toContain(
      'Crear empleado',
    );
    expect(el(f).querySelector('a[href="/gestion/empleados/1/editar"]')).not.toBeNull();
    const etiquetas = Array.from(el(f).querySelectorAll('.etiqueta')).map((e) => e.textContent);
    expect(etiquetas).toEqual(['Activo', 'Inactivo']);
    // un registro ya dado de baja no se puede eliminar de nuevo
    const eliminar = Array.from(el(f).querySelectorAll<HTMLButtonElement>('.peligro'));
    expect(eliminar.map((b) => b.disabled)).toEqual([false, true]);
  });

  it('M-15 usa la API de distribuidores y sus rutas', async () => {
    const listar = vi.fn(() => of([FILAS[0]]));
    montar({ tipo: 'distribuidor' }, { dis: { listar }, emp: { listar: vi.fn() } });
    const f = TestBed.createComponent(ListadoPersonal);
    await f.whenStable();
    expect(listar).toHaveBeenCalledWith('');
    expect(el(f).querySelector('h1')?.textContent).toBe('Distribuidores');
    expect(el(f).querySelector('a[href="/gestion/distribuidores/nuevo"]')).not.toBeNull();
    expect(el(f).textContent).toContain('Mostrando 1 registro');
  });

  it('lista vacía y búsqueda sin resultados muestran su estado', async () => {
    const listar = vi.fn(() => of([] as ResumenDTO[]));
    montar({ tipo: 'empleado' }, { emp: { listar } });
    const f = TestBed.createComponent(ListadoPersonal);
    await f.whenStable();
    expect(el(f).textContent).toContain('Aún no hay empleados registrados.');
    escribir(el(f).querySelector<HTMLInputElement>('#buscar')!, 'zzz');
    await esperar(400);
    await f.whenStable();
    expect(listar).toHaveBeenLastCalledWith('zzz');
    expect(el(f).textContent).toContain('Ningún empleado coincide con la búsqueda.');
  });

  it('error de carga: aviso con Reintentar', async () => {
    let falla = true;
    const listar = vi.fn(() =>
      falla ? throwError(() => ({ estado: 500, mensaje: 'Servidor caído' })) : of(FILAS),
    );
    montar({ tipo: 'empleado' }, { emp: { listar } });
    const f = TestBed.createComponent(ListadoPersonal);
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('Servidor caído');
    falla = false;
    boton(el(f), 'Reintentar').click();
    await f.whenStable();
    expect(el(f).textContent).toContain('Ana Gómez');
    expect(el(f).querySelector('.aviso.error')).toBeNull();
  });

  it('eliminar: pide confirmación, llama DELETE, avisa y recarga; cancelar no elimina', async () => {
    const eliminar = vi.fn(() => of(undefined));
    const listar = vi.fn(() => of(FILAS));
    montar({ tipo: 'empleado' }, { emp: { listar, eliminar } });
    const f = TestBed.createComponent(ListadoPersonal);
    await f.whenStable();
    el(f).querySelector<HTMLButtonElement>('.peligro')!.click();
    await f.whenStable();
    const dialogo = el(f).querySelector<HTMLElement>('[role="dialog"]')!;
    expect(dialogo.textContent).toContain('Ana Gómez');
    expect(dialogo.textContent).toContain('La baja es lógica');
    boton(dialogo, 'Cancelar').click();
    await f.whenStable();
    expect(eliminar).not.toHaveBeenCalled();
    expect(el(f).querySelector('[role="dialog"]')).toBeNull();

    el(f).querySelector<HTMLButtonElement>('.peligro')!.click();
    await f.whenStable();
    boton(el(f).querySelector<HTMLElement>('[role="dialog"]')!, 'Dar de baja').click();
    await f.whenStable();
    expect(eliminar).toHaveBeenCalledWith(1);
    expect(listar).toHaveBeenCalledTimes(2);
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain(
      'Se dio de baja a Ana Gómez',
    );
    expect(el(f).querySelector('[role="dialog"]')).toBeNull();
  });

  it('eliminar con error 404/503: el mensaje queda dentro del diálogo', async () => {
    montar(
      { tipo: 'empleado' },
      {
        emp: {
          listar: () => of(FILAS),
          eliminar: () =>
            throwError(() => ({
              estado: 503,
              codigo: 'CONTINGENCIA',
              mensaje: 'Modo contingencia',
            })),
        },
      },
    );
    const f = TestBed.createComponent(ListadoPersonal);
    await f.whenStable();
    el(f).querySelector<HTMLButtonElement>('.peligro')!.click();
    await f.whenStable();
    boton(el(f).querySelector<HTMLElement>('[role="dialog"]')!, 'Dar de baja').click();
    await f.whenStable();
    expect(el(f).querySelector('[role="dialog"] .aviso.error')?.textContent).toContain(
      'Modo contingencia',
    );
  });
});

describe('M-13 Formulario de empleado / distribuidor', () => {
  const llenar = (f: { nativeElement: unknown }, extra: Record<string, string> = {}) => {
    const v: Record<string, string> = {
      nombre: 'Marcela Cruz',
      documento: '1098765432',
      correo: 'marcela@chibchaweb.com',
      telefono: '3101234567',
      idRol: '2',
      ...extra,
    };
    for (const [k, valor] of Object.entries(v)) {
      const c = el(f).querySelector<HTMLInputElement | HTMLSelectElement>(`#${k}`);
      if (c) escribir(c, valor);
    }
  };

  it('vacío: no envía, marca los campos y muestra "Faltan campos obligatorios"', async () => {
    const crear = vi.fn();
    montar({ tipo: 'empleado' }, { emp: { roles: () => of(ROLES), crear } });
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    expect(el(f).querySelector('h1')?.textContent).toContain('Crear empleado');
    expect(el(f).querySelectorAll('#idRol option').length).toBe(3);
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    expect(crear).not.toHaveBeenCalled();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('Faltan campos');
    expect(el(f).querySelectorAll('.campo .error').length).toBeGreaterThanOrEqual(4);
  });

  it('crea con POST (cuerpo EmpleadoDTO) y va al detalle con el aviso', async () => {
    const crear = vi.fn(() => of({ id: 9 }));
    montar({ tipo: 'empleado' }, { emp: { roles: () => of(ROLES), crear } });
    const nav = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    llenar(f);
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    expect(crear).toHaveBeenCalledWith({
      nombre: 'Marcela Cruz',
      documento: '1098765432',
      correo: 'marcela@chibchaweb.com',
      telefono: '3101234567',
      idRol: 2,
    });
    expect(nav).toHaveBeenCalledWith(['/gestion/empleados', 9], {
      state: { aviso: 'Empleado creado.' },
    });
  });

  it('409 DUPLICADO y 422 con campo salen debajo del campo; limpian al editar', async () => {
    const crear = vi
      .fn()
      .mockReturnValueOnce(
        throwError(() => ({
          estado: 409,
          codigo: 'DUPLICADO',
          campo: 'correo',
          mensaje: 'Ya existe un usuario con ese correo.',
        })),
      )
      .mockReturnValueOnce(
        throwError(() => ({
          estado: 422,
          codigo: 'VALIDACION',
          campo: 'documento',
          mensaje: 'El documento no es válido.',
        })),
      );
    montar({ tipo: 'empleado' }, { emp: { roles: () => of(ROLES), crear } });
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    llenar(f);
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    const correo = el(f).querySelector('#correo')!.closest('.campo')!;
    expect(correo.querySelector('.error')?.textContent).toContain('ese correo');
    escribir(el(f).querySelector<HTMLInputElement>('#correo')!, 'otro@chibchaweb.com');
    await f.whenStable();
    expect(correo.querySelector('.error')).toBeNull();
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    expect(el(f).querySelector('#documento')!.closest('.campo')!.textContent).toContain(
      'El documento no es válido.',
    );
    expect(el(f).querySelector('.acciones')!.previousElementSibling?.classList).not.toContain(
      'aviso',
    );
  });

  it('error sin campo (503) va al aviso sobre los botones', async () => {
    montar(
      { tipo: 'empleado' },
      {
        emp: {
          roles: () => of(ROLES),
          crear: () =>
            throwError(() => ({ estado: 503, codigo: 'CONTINGENCIA', mensaje: 'En contingencia' })),
        },
      },
    );
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    llenar(f);
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('En contingencia');
  });

  it('editar: carga el detalle (PUT al guardar) y 404 muestra "no encontrado"', async () => {
    const modificar = vi.fn(() => of(undefined));
    montar(
      { tipo: 'empleado' },
      { emp: { roles: () => of(ROLES), detalle: () => of(DET_EMP), modificar } },
      { id: '7' },
    );
    const nav = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    await esperar();
    await f.whenStable();
    expect(el(f).querySelector('h1')?.textContent).toContain('Editar empleado');
    expect(el(f).querySelector<HTMLInputElement>('#documento')!.value).toBe('1000000007');
    expect(el(f).querySelector<HTMLSelectElement>('#idRol')!.value).toBe('2');
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    expect(modificar).toHaveBeenCalledWith(7, expect.objectContaining({ idRol: 2 }));
    expect(nav).toHaveBeenCalled();
  });

  it('editar un id inexistente muestra el estado 404 con enlace al listado', async () => {
    montar(
      { tipo: 'empleado' },
      {
        emp: {
          roles: () => of(ROLES),
          detalle: () => throwError(() => ({ estado: 404, codigo: 'NO_ENCONTRADO', mensaje: 'x' })),
        },
      },
      { id: '99' },
    );
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    await esperar();
    await f.whenStable();
    expect(el(f).textContent).toContain('No encontramos el empleado que buscas');
    expect(el(f).querySelector('form')).toBeNull();
    expect(el(f).querySelector('a[href="/gestion/empleados"]')).not.toBeNull();
  });

  it('modo distribuidor: sin cargo, POST de DistribuidorDTO y muestra el código asignado', async () => {
    const crear = vi.fn(() => of({ id: 4, codigo: 'DIS-ABC123' }));
    montar({ tipo: 'distribuidor' }, { dis: { crear }, emp: { roles: vi.fn() } });
    const nav = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    const f = TestBed.createComponent(FormularioPersonal);
    await f.whenStable();
    expect(el(f).querySelector('#idRol')).toBeNull();
    expect(el(f).querySelector('h1')?.textContent).toContain('Crear distribuidor');
    llenar(f);
    boton(el(f), 'Guardar').click();
    await f.whenStable();
    expect(crear).toHaveBeenCalledWith({
      nombre: 'Marcela Cruz',
      documento: '1098765432',
      correo: 'marcela@chibchaweb.com',
      telefono: '3101234567',
    });
    expect(nav).toHaveBeenCalledWith(['/gestion/distribuidores', 4], {
      state: { aviso: 'Distribuidor creado. Código asignado: DIS-ABC123.' },
    });
  });
});

describe('M-14 Detalle', () => {
  it('empleado: datos, cargo y estado, solo con campos del contrato', async () => {
    montar({ tipo: 'empleado' }, { emp: { detalle: () => of(DET_EMP) } }, { id: '7' });
    const f = TestBed.createComponent(DetallePersonal);
    await f.whenStable();
    const t = el(f).textContent!;
    expect(t).toContain('Jorge Suárez Ramírez');
    expect(t).toContain('Empleado · activo desde 2026');
    expect(t).toContain('1000000007');
    expect(t).toContain('Soporte');
    expect(t).toContain('2 mar 2026');
    expect(el(f).querySelector('.etiqueta')?.textContent).toBe('Activo');
    expect(el(f).querySelector('a[href$="/editar"]')).not.toBeNull();
  });

  it('distribuidor: código, categoría y referidos', async () => {
    montar({ tipo: 'distribuidor' }, { dis: { detalle: () => of(DET_DIS) } }, { id: '10' });
    const f = TestBed.createComponent(DetallePersonal);
    await f.whenStable();
    expect(el(f).querySelector('.codigo')?.textContent).toBe('DIS-ANDES1');
    expect(el(f).textContent).toContain('Premium');
    expect(el(f).textContent).toContain('128');
  });

  it('404 → no encontrado', async () => {
    montar(
      { tipo: 'empleado' },
      { emp: { detalle: () => throwError(() => ({ estado: 404, mensaje: 'x' })) } },
      { id: '1' },
    );
    const f = TestBed.createComponent(DetallePersonal);
    await f.whenStable();
    expect(el(f).textContent).toContain('No encontramos el empleado que buscas');
  });

  it('Eliminar confirma, da de baja y recarga el detalle inactivo', async () => {
    let activo = 'true';
    const eliminar = vi.fn(() => {
      activo = 'false';
      return of(undefined);
    });
    const detalle = vi.fn(() =>
      of({
        ...DET_EMP,
        campos: [...DET_EMP.campos.filter((c) => !c.startsWith('activo')), `activo: ${activo}`],
      }),
    );
    montar({ tipo: 'empleado' }, { emp: { detalle, eliminar } }, { id: '7' });
    const f = TestBed.createComponent(DetallePersonal);
    await f.whenStable();
    boton(el(f), 'Eliminar').click();
    await f.whenStable();
    boton(el(f).querySelector<HTMLElement>('[role="dialog"]')!, 'Dar de baja').click();
    await f.whenStable();
    expect(eliminar).toHaveBeenCalledWith(7);
    expect(el(f).textContent).toContain('Empleado · dado de baja');
    expect(el(f).querySelector('.etiqueta')?.textContent).toBe('Inactivo');
    expect(boton(el(f), 'Eliminar').disabled).toBe(true);
  });
});

describe('M-16 Clientes', () => {
  const CLI: ResumenDTO[] = [
    { id: 1, titulo: 'Steven Navarro', subtitulo: 'steven@correo.co · cafe', estado: 'ACTIVO' },
  ];
  const DET_CLI: DetalleDTO = {
    id: 1,
    titulo: 'Steven Navarro',
    campos: [
      'nombre: Steven Navarro',
      'correo: steven@correo.co',
      'telefono: 300',
      'lineaResidencia: Calle 1',
      'ciudadResidencia: Sogamoso',
      'lineaFacturacion: Calle 1',
      'ciudadFacturacion: Sogamoso',
      'tarjeta: VISA •••• 1111',
      'vencimiento: 2028-08-01',
      'sitio: cafe.chibchaweb.com',
      'plataforma: UNIX',
      'paquete: Chibcha-Platino',
      'plan: Anual',
      'montoPeriodo: 204.00',
      'fechaCorte: 2027-09-14',
      'distribuidor: ',
      'activo: true',
    ],
  };

  it('lista con filtro y "Ver detalle" abre el panel lateral con GET /consultas/CLIENTE/{id}', async () => {
    const detalle = vi.fn(() => of(DET_CLI));
    const basico = vi.fn(() => of(CLI));
    montar(null, { con: { basico, detalle } });
    const f = TestBed.createComponent(ClientesGestion);
    await f.whenStable();
    expect(basico).toHaveBeenCalledWith('CLIENTE', '');
    expect(el(f).querySelector('aside')).toBeNull();
    boton(el(f), 'Ver detalle').click();
    await f.whenStable();
    expect(detalle).toHaveBeenCalledWith('CLIENTE', 1);
    const panel = el(f).querySelector('aside')!;
    expect(panel.textContent).toContain('cafe.chibchaweb.com');
    expect(panel.textContent).toContain('Sin distribuidor');
    expect(panel.textContent).toContain('VISA •••• 1111 · vence 08/28');
    boton(panel as HTMLElement, 'Cerrar').click();
    await f.whenStable();
    expect(el(f).querySelector('aside')).toBeNull();
  });

  it('detalle 404: el panel lo indica; sin clientes: texto de vacío', async () => {
    montar(null, {
      con: {
        basico: () => of(CLI),
        detalle: () => throwError(() => ({ estado: 404, codigo: 'NO_ENCONTRADO', mensaje: 'x' })),
      },
    });
    const f = TestBed.createComponent(ClientesGestion);
    await f.whenStable();
    boton(el(f), 'Ver detalle').click();
    await f.whenStable();
    expect(el(f).querySelector('aside .aviso.error')?.textContent).toContain('ya no existe');

    TestBed.resetTestingModule();
    montar(null, { con: { basico: () => of([]) } });
    const g = TestBed.createComponent(ClientesGestion);
    await g.whenStable();
    expect(el(g).textContent).toContain('Aún no hay clientes registrados.');
  });
});
