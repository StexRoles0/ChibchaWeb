import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { firstValueFrom, Observable } from 'rxjs';
import { ClientesApi } from '../clientes.api';
import { ConsultasApi } from '../consultas.api';
import { ContingenciaApi } from '../contingencia.api';
import { DominiosApi } from '../dominios.api';
import { MigracionApi } from '../migracion.api';
import { SoporteApi } from '../soporte.api';
import { erroresInterceptor } from '../../interceptores';
import { reiniciarSimulado } from './almacen';
import { abrirSesionCliente } from './estado';
import { fijarUsuarioSimulado } from './sesiones';
import { simuladoInterceptor } from './simulado.interceptor';

const w = <T>(o: Observable<T>) => firstValueFrom(o);
const falla = async (p: Promise<unknown>) => {
  try {
    await p;
  } catch (e) {
    return e as { estado: number; codigo: string; campo?: string; mensaje: string };
  }
  throw new Error('debía fallar');
};

function preparar(usuario: 'cliente' | 'soporte' | 'admin' | 'gestion') {
  reiniciarSimulado();
  localStorage.removeItem('chibchaweb.simulado.falla');
  if (usuario === 'cliente') abrirSesionCliente('steven@correo.co');
  else fijarUsuarioSimulado(usuario);
  TestBed.configureTestingModule({
    providers: [
      provideRouter([
        { path: 'acceso', children: [] },
        { path: 'no-autorizado', children: [] },
      ]),
      provideHttpClient(withInterceptors([erroresInterceptor, simuladoInterceptor])),
    ],
  });
  TestBed.inject(HttpClient);
}

describe('modo simulado · dominios (CU-DOM-01/02)', () => {
  let api: DominiosApi;
  beforeEach(() => {
    preparar('cliente');
    api = TestBed.inject(DominiosApi);
  });

  it('lista las solicitudes sembradas del cliente, la más reciente primero', async () => {
    const l = await w(api.solicitudes());
    expect(l.map((s) => s.titulo)).toEqual([
      'cafedeboyaca.net',
      'tostadoresboyaca.co',
      'cafedeboyaca.com',
    ]);
    expect(l.map((s) => s.estado)).toEqual(['REGISTRADA', 'FALLIDA', 'ENVIADA']);
  });

  it('POST encadena registrar y enviar: 201 con estado ENVIADA y aparece en la lista', async () => {
    const r = await w(api.solicitar({ nombre: 'Mi-Tienda', extension: '.org' }));
    expect(r.estado).toBe('ENVIADA');
    expect((await w(api.solicitudes()))[0]).toMatchObject({
      titulo: 'mi-tienda.org',
      estado: 'ENVIADA',
    });
  });

  it('un dominio que contiene "rechazo" lo rechaza el registrador: 201 con FALLIDA', async () => {
    const r = await w(api.solicitar({ nombre: 'tienda-rechazo', extension: '.co' }));
    expect(r.estado).toBe('FALLIDA');
  });

  it('RN-16: formato inválido, 64 caracteres y extensión no admitida son 422 con campo', async () => {
    for (const nombre of ['-tienda', 'tienda-', 'tien da', 'ñandú', 'a'.repeat(64), '']) {
      const e = await falla(w(api.solicitar({ nombre, extension: '.com' })));
      expect([e.estado, e.codigo, e.campo]).toEqual([422, 'VALIDACION', 'nombre']);
    }
    await w(api.solicitar({ nombre: 'a'.repeat(63), extension: '.com' }));
    const e = await falla(w(api.solicitar({ nombre: 'ok', extension: '.xyz' as never })));
    expect(e.campo).toBe('extension');
  });

  it('con contingencia forzada responde 503 CONTINGENCIA y deja el evento en el respaldo', async () => {
    localStorage.setItem('chibchaweb.simulado.falla', 'contingencia');
    const e = await falla(w(api.solicitar({ nombre: 'tienda', extension: '.com' })));
    expect([e.estado, e.codigo]).toEqual([503, 'CONTINGENCIA']);
    localStorage.setItem('chibchaweb.simulado.falla', '');
    fijarUsuarioSimulado('admin');
    const p = await w(TestBed.inject(ContingenciaApi).pendientes());
    expect(p.length).toBe(4);
    expect(p[3].titulo).toBe('Solicitud de dominio enviada');
  });

  it('un empleado no puede usar los dominios (403)', async () => {
    fijarUsuarioSimulado('soporte');
    expect((await falla(w(api.solicitudes()))).estado).toBe(403);
  });
});

describe('modo simulado · soporte (CU-SOP-01/02/03)', () => {
  beforeEach(() => preparar('cliente'));

  it('el cliente ve sus sitios y sus tickets (P-06, consultarMisTickets)', async () => {
    const sitios = await w(TestBed.inject(ClientesApi).sitios());
    expect(sitios[0].titulo).toBe('cafedeboyaca.chibchaweb.com');
    const mios = await w(TestBed.inject(SoporteApi).mios());
    expect(mios.map((t) => t.id)).toEqual([1042, 1038, 991]);
    expect(mios[0]).toMatchObject({
      titulo: 'RENDIMIENTO',
      subtitulo: 'Soporte',
      estado: 'ABIERTO',
    });
  });

  it('registra un ticket ABIERTO en el nivel 1, con sitio propio o sin sitio', async () => {
    const api = TestBed.inject(SoporteApi);
    const sitios = await w(TestBed.inject(ClientesApi).sitios());
    const { id } = await w(
      api.crear({ categoria: 'CORREO', descripcion: 'No llega', idSitio: sitios[0].id }),
    );
    await w(api.crear({ categoria: 'OTRA', descripcion: 'Sin sitio' }));
    const mios = await w(api.mios());
    expect(mios.length).toBe(5);
    expect(mios.find((t) => t.id === id)).toMatchObject({
      subtitulo: 'Soporte',
      estado: 'ABIERTO',
    });
  });

  it('422 por campo: sin categoría, sin descripción o con un sitio ajeno', async () => {
    const api = TestBed.inject(SoporteApi);
    expect((await falla(w(api.crear({ categoria: '', descripcion: 'x' })))).campo).toBe(
      'categoria',
    );
    expect((await falla(w(api.crear({ categoria: 'OTRA', descripcion: '  ' })))).campo).toBe(
      'descripcion',
    );
    const e = await falla(w(api.crear({ categoria: 'OTRA', descripcion: 'x', idSitio: 999 })));
    expect([e.estado, e.codigo, e.campo]).toEqual([422, 'REGLA_NEGOCIO', 'idSitio']);
  });

  it('el cliente no puede ver la bandeja (403)', async () => {
    expect((await falla(w(TestBed.inject(SoporteApi).diarios('2026-11-16')))).estado).toBe(403);
  });
});

describe('modo simulado · bandeja de soporte', () => {
  let api: SoporteApi;
  const hoy = () => {
    const h = new Date();
    return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, '0')}-${String(h.getDate()).padStart(2, '0')}`;
  };
  beforeEach(() => {
    preparar('soporte');
    api = TestBed.inject(SoporteApi);
  });

  it('RN-24: creados hoy más todos los abiertos o escalados, del más reciente al más antiguo', async () => {
    const l = await w(api.diarios(hoy()));
    expect(l.map((t) => t.id)).toEqual([1042, 1041, 1038, 1035, 1029]);
    expect(l.some((t) => t.estado === 'RESUELTO')).toBe(false);
  });

  it('una fecha con resueltos creados ese día los incluye y una fecha mal escrita es 422', async () => {
    const d = new Date();
    d.setDate(d.getDate() - 6);
    const f = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    expect((await w(api.diarios(f))).map((t) => t.id)).toContain(1020);
    expect((await falla(w(api.diarios('ayer')))).campo).toBe('fecha');
  });

  it('detalle con claves fijas y 404 si no existe', async () => {
    const d = await w(api.detalle(1038));
    expect(d.campos.map((c) => c.split(':')[0])).toEqual([
      'categoria',
      'estado',
      'nivel',
      'reportante',
      'sitio',
      'fechaCreacion',
      'descripcion',
      'movimiento',
    ]);
    expect((await falla(w(api.detalle(7)))).estado).toBe(404);
  });

  it('GET /consultas/TICKET reutiliza los mismos datos', async () => {
    const c = TestBed.inject(ConsultasApi);
    expect((await w(c.basico('TICKET', 'caché'))).length).toBe(0);
    expect((await w(c.basico('TICKET', '1041'))).map((t) => t.id)).toEqual([1041]);
    expect((await w(c.detalle('TICKET', 1042))).titulo).toBe('Ticket #1042');
  });

  it('escalar sube de nivel, deja un movimiento y exige observación (422)', async () => {
    expect((await falla(w(api.enrutar(1042, { escalar: true, observacion: ' ' })))).campo).toBe(
      'observacion',
    );
    await w(api.enrutar(1042, { escalar: true, observacion: 'Revisar caché' }));
    const d = await w(api.detalle(1042));
    expect(d.campos).toContain('estado: ESCALADO');
    expect(d.campos).toContain('nivel: Gestión');
    expect(
      d.campos.some(
        (c) =>
          c.startsWith('movimiento:') && c.includes('|Ana Ruiz|ESCALADO|Gestión|Revisar caché'),
      ),
    ).toBe(true);
  });

  it('409 ESTADO_INVALIDO al escalar en el último nivel o un ticket resuelto; resolver sí se puede', async () => {
    const ultimo = await falla(w(api.enrutar(1029, { escalar: true, observacion: 'x' })));
    expect([ultimo.estado, ultimo.codigo]).toEqual([409, 'ESTADO_INVALIDO']);
    const resuelto = await falla(w(api.enrutar(1020, { escalar: true, observacion: 'x' })));
    expect(resuelto.estado).toBe(409);
    await w(api.enrutar(1029, { escalar: false, observacion: 'Listo' }));
    expect((await w(api.detalle(1029))).campos).toContain('estado: RESUELTO');
    expect((await falla(w(api.enrutar(5, { escalar: false, observacion: 'x' })))).estado).toBe(404);
  });

  it('un empleado de gestión no atiende tickets (403)', async () => {
    fijarUsuarioSimulado('gestion');
    expect((await falla(w(api.diarios(hoy())))).estado).toBe(403);
  });
});

describe('modo simulado · migración (CU-MIG-01)', () => {
  let api: MigracionApi;
  beforeEach(() => {
    preparar('admin');
    api = TestBed.inject(MigracionApi);
  });

  it('simula con válidos, inválidos y log "NIVEL|tipo|idLegado|mensaje"', async () => {
    const r = await w(api.simular());
    expect(r.validos + r.invalidos).toBe(r.entradas.length);
    expect(r.invalidos).toBe(r.entradas.filter((e) => e.startsWith('ERROR|')).length);
    expect(r.entradas.every((e) => e.split('|').length >= 4)).toBe(true);
    expect(new Set(r.entradas.map((e) => e.split('|')[1]))).toEqual(
      new Set(['CLIENTE', 'HOSTING', 'PAGO']),
    );
  });

  it('confirmar una simulación la ejecuta; confirmar otra vez es 409 (RN-25)', async () => {
    const { idProceso } = await w(api.simular());
    expect((await w(api.confirmar(idProceso))).estado).toBe('EJECUTADA');
    const e = await falla(w(api.confirmar(idProceso)));
    expect([e.estado, e.codigo]).toEqual([409, 'ESTADO_INVALIDO']);
    expect((await falla(w(api.cancelar(idProceso)))).estado).toBe(409);
  });

  it('si una escritura falla, el proceso queda REVERTIDA (RN-27)', async () => {
    const { idProceso } = await w(api.simular());
    localStorage.setItem('chibchaweb.simulado.falla', 'migracion');
    expect((await w(api.confirmar(idProceso))).estado).toBe('REVERTIDA');
  });

  it('cancelar una simulación la deja CANCELADA y ya no se confirma; un proceso inexistente es 404', async () => {
    const { idProceso } = await w(api.simular());
    expect((await w(api.cancelar(idProceso))).estado).toBe('CANCELADA');
    expect((await falla(w(api.confirmar(idProceso)))).estado).toBe(409);
    expect((await falla(w(api.confirmar(99)))).estado).toBe(404);
  });

  it('sin la operación MIGRAR_DATOS es 403', async () => {
    fijarUsuarioSimulado('gestion');
    expect((await falla(w(api.simular()))).estado).toBe(403);
  });
});

describe('modo simulado · contingencia (RT04)', () => {
  let api: ContingenciaApi;
  beforeEach(() => {
    preparar('admin');
    api = TestBed.inject(ContingenciaApi);
  });

  it('lista los tres eventos pendientes con tipo y algoritmo', async () => {
    const p = await w(api.pendientes());
    expect(p.map((e) => [e.titulo, e.subtitulo])).toEqual([
      ['Suscripcion.registrar_pago', 'AES'],
      ['SolicitudDominio.insertar', 'AES'],
      ['Comision.registrar_cheque', 'ChaCha20'],
    ]);
  });

  it('acepta los cuatro algoritmos y rechaza otro con 422 en `nombre`', async () => {
    for (const a of ['AES', 'ChaCha20', 'Camellia', 'Twofish'] as const) {
      await w(api.cambiarAlgoritmo(a));
    }
    const e = await falla(w(api.cambiarAlgoritmo('DES' as never)));
    expect([e.estado, e.campo]).toEqual([422, 'nombre']);
  });

  it('sincronizar vacía el respaldo; con la base caída es 503 y no lo vacía (RN-30)', async () => {
    localStorage.setItem('chibchaweb.simulado.falla', 'contingencia');
    expect((await falla(w(api.sincronizar()))).codigo).toBe('CONTINGENCIA');
    expect((await w(api.pendientes())).length).toBe(3);
    localStorage.setItem('chibchaweb.simulado.falla', '');
    expect(await w(api.sincronizar())).toEqual({ sincronizados: 3 });
    expect(await w(api.pendientes())).toEqual([]);
  });

  it('solo con GESTIONAR_CONTINGENCIA (403 para gestión)', async () => {
    fijarUsuarioSimulado('gestion');
    expect((await falla(w(api.pendientes()))).estado).toBe(403);
  });
});
