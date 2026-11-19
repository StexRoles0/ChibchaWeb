import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ContingenciaApi } from '../../core/api/contingencia.api';
import { ResultadoMigracionDTO } from '../../core/api/dto';
import { MigracionApi } from '../../core/api/migracion.api';
import { USUARIOS_SIMULADOS } from '../../core/api/simulado/sesiones';
import { SesionStore } from '../../core/auth/sesion.store';
import { ADMIN_ROUTES } from './admin.routes';
import { Contingencia } from './contingencia';
import { InicioAdmin } from './inicio';
import { Migracion } from './migracion';
import { aEntrada, MigracionStore } from './migracion.store';

const el = (f: { nativeElement: unknown }) => f.nativeElement as HTMLElement;
const boton = (raiz: HTMLElement, texto: string) =>
  Array.from(raiz.querySelectorAll<HTMLButtonElement>('button')).find((b) =>
    b.textContent?.includes(texto),
  )!;

const enDialogo = (raiz: HTMLElement, texto: string) =>
  Array.from(raiz.querySelectorAll<HTMLButtonElement>('[role="dialog"] button')).find((b) =>
    b.textContent?.includes(texto),
  )!;

const SIM: ResultadoMigracionDTO = {
  idProceso: 4,
  validos: 3,
  invalidos: 2,
  entradas: [
    'INFO|CLIENTE|CL-0001|Registro válido',
    'ADVERTENCIA|CLIENTE|CL-0002|Sin teléfono',
    'ERROR|CLIENTE|CL-0003|Dirección: la línea es obligatoria',
    'INFO|HOSTING|HO-0001|Existe en el catálogo',
    'ERROR|PAGO|PG-0001|El monto no es válido',
  ],
};

describe('rutas de administración (docs/ui.md)', () => {
  it('M-18/M-19 piden MIGRAR_DATOS y M-20 GESTIONAR_CONTINGENCIA; ninguna es marcador', () => {
    const hijos = ADMIN_ROUTES[0].children!;
    expect(hijos.map((r) => r.path)).toEqual(['', 'migracion', 'contingencia']);
    for (const r of hijos) {
      expect(r.canActivate?.length).toBe(1);
      expect(r.loadComponent).toBeDefined();
      expect(r.data).toBeUndefined();
    }
  });
});

describe('M-18 Inicio del administrador', () => {
  function montar(contingencia: Partial<ContingenciaApi>, usuario = USUARIOS_SIMULADOS.admin) {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: ContingenciaApi, useValue: contingencia }],
    });
    TestBed.inject(SesionStore).establecer(usuario);
    return TestBed.createComponent(InicioAdmin);
  }

  it('enlaza migración y contingencia y cuenta los eventos en respaldo', async () => {
    const f = montar({ pendientes: () => of([{}, {}, {}] as never[]) });
    await f.whenStable();
    expect(el(f).textContent).toContain('Administración');
    expect(el(f).textContent).toContain('Operaciones técnicas del sistema.');
    expect(el(f).querySelector('a[href="/admin/migracion"]')).not.toBeNull();
    expect(el(f).querySelector('a[href="/admin/contingencia"]')).not.toBeNull();
    expect(el(f).querySelector('.cifra')?.textContent?.trim()).toBe('3');
    expect(el(f).textContent).toContain('Eventos en respaldo');
    // Sin endpoint en el contrato: no se inventan estas tarjetas.
    expect(el(f).textContent).not.toContain('Última migración');
    expect(el(f).textContent).not.toContain('Base de datos');
  });

  it('si el respaldo no se puede consultar muestra un guion y avisa', async () => {
    const f = montar({ pendientes: () => throwError(() => ({ estado: 500 })) });
    await f.whenStable();
    expect(el(f).querySelector('.cifra')?.textContent?.trim()).toBe('—');
    expect(el(f).textContent).toContain('No se pudo consultar el respaldo.');
  });

  it('sin GESTIONAR_CONTINGENCIA no consulta ni muestra el estado', async () => {
    const pendientes = vi.fn(() => of([]));
    const f = montar(
      { pendientes },
      {
        ...USUARIOS_SIMULADOS.admin!,
        operaciones: ['MIGRAR_DATOS'],
      },
    );
    await f.whenStable();
    expect(pendientes).not.toHaveBeenCalled();
    expect(el(f).querySelector('a[href="/admin/contingencia"]')).toBeNull();
    expect(el(f).textContent).not.toContain('Estado del sistema');
  });
});

describe('MigracionStore', () => {
  it('aEntrada separa nivel, tipo, id y mensaje (que puede traer "|")', () => {
    expect(aEntrada('error|pago|PG-1|a|b')).toEqual({
      nivel: 'ERROR',
      tipo: 'PAGO',
      idLegado: 'PG-1',
      mensaje: 'a|b',
    });
  });

  it('resume por tipo: válidos (no ERROR) sobre leídos', async () => {
    TestBed.configureTestingModule({
      providers: [MigracionStore, { provide: MigracionApi, useValue: { simular: () => of(SIM) } }],
    });
    const s = TestBed.inject(MigracionStore);
    await s.simular();
    expect(s.resumen().map((r) => [r.titulo, r.validos, r.leidos])).toEqual([
      ['Clientes', 2, 3],
      ['Registros de hosting', 1, 1],
      ['Historial de pagos', 0, 1],
    ]);
    expect(s.puedeEjecutar()).toBe(true);
  });
});

describe('M-19 Migración', () => {
  function montar(api: Partial<MigracionApi>) {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), MigracionStore, { provide: MigracionApi, useValue: api }],
    });
    TestBed.inject(SesionStore).establecer(USUARIOS_SIMULADOS.admin);
    return TestBed.createComponent(Migracion);
  }

  it('al inicio solo ofrece simular y no hay forma de ejecutar', async () => {
    const f = montar({});
    await f.whenStable();
    expect(el(f).textContent).toContain('Migración de datos legados');
    expect(el(f).textContent).toContain('Aún no hay una simulación');
    expect(boton(el(f), 'Ejecutar simulación')).toBeDefined();
    expect(boton(el(f), 'Ejecutar migración real')).toBeUndefined();
  });

  it('tras simular muestra pasos, tarjetas, log con nivel y habilita Ejecutar y Cancelar', async () => {
    const f = montar({ simular: () => of(SIM) });
    await f.whenStable();
    boton(el(f), 'Ejecutar simulación').click();
    await f.whenStable();
    expect(el(f).textContent).toContain('1 · Simulación completada');
    expect(el(f).textContent).toContain('2 / 3');
    expect(el(f).textContent).toContain('válidos / leídos');
    const filas = Array.from(el(f).querySelectorAll('.log tbody tr'));
    expect(filas.length).toBe(5);
    expect(filas.map((r) => r.className)).toEqual([
      'info',
      'advertencia',
      'error',
      'info',
      'error',
    ]);
    expect(boton(el(f), 'Ejecutar migración real').disabled).toBe(false);
    expect(boton(el(f), 'Cancelar migración').disabled).toBe(false);
    expect(boton(el(f), 'Ejecutar simulación de nuevo')).toBeDefined();
  });

  async function simulada(api: Partial<MigracionApi>) {
    const f = montar({ simular: () => of(SIM), ...api });
    await f.whenStable();
    boton(el(f), 'Ejecutar simulación').click();
    await f.whenStable();
    return f;
  }

  it('ejecutar pide confirmación; EJECUTADA deshabilita los botones y lo anuncia', async () => {
    const confirmar = vi.fn(() => of({ estado: 'EJECUTADA' as const }));
    const f = await simulada({ confirmar });
    boton(el(f), 'Ejecutar migración real').click();
    await f.whenStable();
    expect(confirmar).not.toHaveBeenCalled();
    expect(el(f).querySelector('[role="dialog"]')).not.toBeNull();
    enDialogo(el(f), 'Ejecutar migración').click();
    await f.whenStable();
    await f.whenStable();
    expect(confirmar).toHaveBeenCalledWith(4);
    expect(el(f).querySelector('[role="dialog"]')).toBeNull();
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain('Migración ejecutada');
    expect(el(f).textContent).toContain('3 · Ejecución real completada');
    expect(boton(el(f), 'Ejecutar migración real').disabled).toBe(true);
  });

  it('REVERTIDA se muestra como fallo y permite simular de nuevo', async () => {
    const f = await simulada({ confirmar: () => of({ estado: 'REVERTIDA' as const }) });
    boton(el(f), 'Ejecutar migración real').click();
    await f.whenStable();
    enDialogo(el(f), 'Ejecutar migración').click();
    await f.whenStable();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('revertida');
    expect(el(f).textContent).toContain('3 · Ejecución revertida');
    expect(boton(el(f), 'Ejecutar simulación de nuevo').disabled).toBe(false);
  });

  it('cancelar con confirmación deja CANCELADA', async () => {
    const cancelar = vi.fn(() => of({ estado: 'CANCELADA' as const }));
    const f = await simulada({ cancelar });
    boton(el(f), 'Cancelar migración').click();
    await f.whenStable();
    // El diálogo trae su propio botón "Cancelar migración" (peligro).
    const enDialogo = Array.from(
      el(f).querySelectorAll<HTMLButtonElement>('[role="dialog"] button'),
    ).find((b) => b.textContent?.includes('Cancelar migración'))!;
    enDialogo.click();
    await f.whenStable();
    await f.whenStable();
    expect(cancelar).toHaveBeenCalledWith(4);
    expect(el(f).querySelector('.aviso.advertencia')?.textContent).toContain('cancelada');
    expect(boton(el(f), 'Ejecutar migración real').disabled).toBe(true);
  });

  it('409 ESTADO_INVALIDO al confirmar muestra el mensaje y no cambia el proceso', async () => {
    const f = await simulada({
      confirmar: () =>
        throwError(() => ({
          estado: 409,
          codigo: 'ESTADO_INVALIDO',
          mensaje: 'La migración está ejecutada y no se puede confirmar.',
        })),
    });
    boton(el(f), 'Ejecutar migración real').click();
    await f.whenStable();
    enDialogo(el(f), 'Ejecutar migración').click();
    await f.whenStable();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('no se puede confirmar');
    expect(boton(el(f), 'Ejecutar migración real').disabled).toBe(false);
  });

  it('un error al simular se ve como aviso', async () => {
    const f = montar({
      simular: () => throwError(() => ({ estado: 403, mensaje: 'No tienes permiso.' })),
    });
    await f.whenStable();
    boton(el(f), 'Ejecutar simulación').click();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('No tienes permiso.');
  });
});

describe('M-20 Contingencia', () => {
  const PEND = [
    { id: 1, titulo: 'Cobro ejecutado', subtitulo: 'AES', estado: 'PENDIENTE' },
    { id: 2, titulo: 'Cheque emitido', subtitulo: 'ChaCha20', estado: 'PENDIENTE' },
  ];
  async function montar(api: Partial<ContingenciaApi>) {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: ContingenciaApi, useValue: api }],
    });
    const f = TestBed.createComponent(Contingencia);
    await f.whenStable();
    return f;
  }

  it('muestra los cuatro algoritmos (AES elegido), la tabla de pendientes y el contador', async () => {
    const f = await montar({ pendientes: () => of(PEND) });
    expect(el(f).textContent).toContain('Contingencia de base de datos');
    const radios = Array.from(el(f).querySelectorAll<HTMLInputElement>('input[type="radio"]'));
    expect(radios.map((r) => r.value)).toEqual(['AES', 'ChaCha20', 'Camellia', 'Twofish']);
    expect(radios.find((r) => r.checked)?.value).toBe('AES');
    expect(el(f).querySelectorAll('tbody tr').length).toBe(2);
    expect(el(f).textContent).toContain('2 eventos pendientes');
    expect(boton(el(f), 'Sincronizar respaldo (2)').disabled).toBe(false);
  });

  it('Aplicar manda el algoritmo elegido y confirma', async () => {
    const cambiarAlgoritmo = vi.fn(() => of(undefined));
    const f = await montar({ pendientes: () => of([]), cambiarAlgoritmo });
    const twofish = el(f).querySelector<HTMLInputElement>('input[value="Twofish"]')!;
    twofish.click();
    await f.whenStable();
    boton(el(f), 'Aplicar algoritmo').click();
    await f.whenStable();
    expect(cambiarAlgoritmo).toHaveBeenCalledWith('Twofish');
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain('Twofish');
  });

  it('un error al aplicar el algoritmo se muestra', async () => {
    const f = await montar({
      pendientes: () => of([]),
      cambiarAlgoritmo: () =>
        throwError(() => ({
          estado: 422,
          codigo: 'VALIDACION',
          mensaje: 'El algoritmo no está admitido.',
        })),
    });
    boton(el(f), 'Aplicar algoritmo').click();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('no está admitido');
  });

  it('sin pendientes: estado vacío y Sincronizar deshabilitado', async () => {
    const f = await montar({ pendientes: () => of([]) });
    expect(el(f).textContent).toContain('No hay eventos pendientes en el respaldo.');
    expect(el(f).textContent).toContain('0 eventos pendientes');
    expect(boton(el(f), 'Sincronizar respaldo (0)').disabled).toBe(true);
  });

  it('sincroniza, recarga y confirma cuántos eventos reinsertó', async () => {
    const pendientes = vi.fn().mockReturnValueOnce(of(PEND)).mockReturnValue(of([]));
    const sincronizar = vi.fn(() => of({ sincronizados: 2 }));
    const f = await montar({ pendientes, sincronizar });
    boton(el(f), 'Sincronizar respaldo (2)').click();
    await f.whenStable();
    await f.whenStable();
    expect(sincronizar).toHaveBeenCalled();
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain(
      'Se sincronizaron 2 eventos',
    );
    expect(el(f).querySelectorAll('tbody tr td.vacio').length).toBe(1);
  });

  it('si la sincronización se detiene a medias lo advierte y conserva el respaldo (RN-30)', async () => {
    const pendientes = vi
      .fn()
      .mockReturnValueOnce(of(PEND))
      .mockReturnValue(of([PEND[1]]));
    const f = await montar({ pendientes, sincronizar: () => of({ sincronizados: 1 }) });
    boton(el(f), 'Sincronizar respaldo (2)').click();
    await f.whenStable();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.advertencia')?.textContent).toContain('1 de 2');
    expect(el(f).textContent).toContain('1 evento pendiente');
  });

  it('503 CONTINGENCIA al sincronizar: la base sigue caída y el respaldo no cambia', async () => {
    const f = await montar({
      pendientes: () => of(PEND),
      sincronizar: () =>
        throwError(() => ({ estado: 503, codigo: 'CONTINGENCIA', mensaje: 'contingencia' })),
    });
    boton(el(f), 'Sincronizar respaldo (2)').click();
    await f.whenStable();
    expect(el(f).querySelector('.aviso.advertencia')?.textContent).toContain('sigue sin responder');
    expect(el(f).querySelectorAll('tbody tr').length).toBe(2);
  });

  it('si no se puede consultar el respaldo ofrece Reintentar', async () => {
    const f = await montar({ pendientes: () => throwError(() => ({ mensaje: 'Sin conexión.' })) });
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('Sin conexión.');
    expect(boton(el(f), 'Reintentar')).toBeDefined();
  });
});
