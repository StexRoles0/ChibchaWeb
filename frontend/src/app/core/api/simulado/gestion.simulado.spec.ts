import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConsultasApi } from '../consultas.api';
import { DistribuidoresApi } from '../distribuidores.api';
import { EmpleadosApi } from '../empleados.api';
import { reiniciarSimulado } from './almacen';
import { fijarUsuarioSimulado } from './sesiones';
import { simuladoInterceptor } from './simulado.interceptor';
import { erroresInterceptor } from '../../interceptores';

const persona = (o: Record<string, unknown> = {}) => ({
  nombre: 'Marcela Cruz',
  documento: '1098765432',
  correo: 'marcela.cruz@chibchaweb.com',
  telefono: '3101234567',
  idRol: 2,
  ...o,
});

describe('modo simulado · gestión (CON-01/02, EMP-01..04, DIS-01..04)', () => {
  let empleados: EmpleadosApi;
  let distribuidores: DistribuidoresApi;
  let consultas: ConsultasApi;
  const w = <T>(o: import('rxjs').Observable<T>) => firstValueFrom(o);
  const falla = async (p: Promise<unknown>) => {
    try {
      await p;
    } catch (e) {
      return e as { estado: number; codigo: string; campo?: string; mensaje: string };
    }
    throw new Error('debía fallar');
  };

  beforeEach(() => {
    reiniciarSimulado();
    fijarUsuarioSimulado('gestion');
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'acceso', children: [] },
          { path: 'no-autorizado', children: [] },
        ]),
        provideHttpClient(withInterceptors([erroresInterceptor, simuladoInterceptor])),
      ],
    });
    empleados = TestBed.inject(EmpleadosApi);
    distribuidores = TestBed.inject(DistribuidoresApi);
    consultas = TestBed.inject(ConsultasApi);
    TestBed.inject(HttpClient);
  });

  it('roles del catálogo y listado con los empleados sembrados', async () => {
    expect((await w(empleados.roles())).map((r) => r.titulo)).toEqual([
      'Gestión',
      'Soporte',
      'Administrador',
    ]);
    const lista = await w(empleados.listar());
    expect(lista.map((r) => r.titulo)).toContain('Gabriela Gestión');
    expect(lista.find((r) => r.titulo === 'Sara Díaz')?.estado).toBe('INACTIVO');
  });

  it('el filtro busca sin distinguir mayúsculas en nombre, correo o documento', async () => {
    expect((await w(empleados.listar('SERGIO'))).map((r) => r.titulo)).toEqual(['Sergio Soporte']);
    expect((await w(empleados.listar('admin@'))).map((r) => r.titulo)).toEqual(['Ana Administra']);
    expect((await w(empleados.listar('e-1001'))).length).toBe(1);
    expect(await w(empleados.listar('nadie-coincide'))).toEqual([]);
  });

  it('crear empleado: 201 {id}; aparece en el listado y en el detalle con claves fijas', async () => {
    const { id } = await w(empleados.crear(persona()));
    expect((await w(empleados.listar('marcela'))).length).toBe(1);
    const d = await w(empleados.detalle(id));
    expect(d.campos).toEqual(
      expect.arrayContaining([
        'nombre: Marcela Cruz',
        'documento: 1098765432',
        'idRol: 2',
        'rol: Soporte',
        'activo: true',
      ]),
    );
    expect(d.campos.some((c) => c.startsWith('fechaRegistro: '))).toBe(true);
  });

  it('modificar empleado se refleja; eliminar es baja lógica (queda INACTIVO)', async () => {
    const { id } = await w(empleados.crear(persona()));
    await w(empleados.modificar(id, persona({ nombre: 'Marcela C. Cruz', idRol: 3 })));
    expect((await w(empleados.detalle(id))).titulo).toBe('Marcela C. Cruz');
    await w(empleados.eliminar(id));
    const fila = (await w(empleados.listar('marcela')))[0];
    expect(fila.estado).toBe('INACTIVO');
  });

  it('422 con campo: vacío, formato de correo, teléfono y cargo inexistente', async () => {
    expect(await falla(w(empleados.crear(persona({ nombre: ' ' }))))).toMatchObject({
      estado: 422,
      codigo: 'VALIDACION',
      campo: 'nombre',
    });
    expect((await falla(w(empleados.crear(persona({ correo: 'sin-arroba' }))))).campo).toBe(
      'correo',
    );
    expect((await falla(w(empleados.crear(persona({ telefono: '12' }))))).campo).toBe('telefono');
    expect((await falla(w(empleados.crear(persona({ idRol: 99 }))))).campo).toBe('idRol');
  });

  it('409 DUPLICADO con el campo: correo y documento repetidos (también al modificar)', async () => {
    expect(
      await falla(w(empleados.crear(persona({ correo: 'soporte@chibchaweb.co' })))),
    ).toMatchObject({ estado: 409, codigo: 'DUPLICADO', campo: 'correo' });
    expect((await falla(w(empleados.crear(persona({ documento: 'E-1001' }))))).campo).toBe(
      'documento',
    );
    const { id } = await w(empleados.crear(persona()));
    expect(
      (await falla(w(empleados.modificar(id, persona({ correo: 'admin@chibchaweb.co' }))))).campo,
    ).toBe('correo');
    // su propio correo no cuenta como duplicado
    await w(empleados.modificar(id, persona({ telefono: '3109999999' })));
  });

  it('404 NO_ENCONTRADO en detalle, modificación y baja', async () => {
    expect((await falla(w(empleados.detalle(999)))).codigo).toBe('NO_ENCONTRADO');
    expect((await falla(w(empleados.modificar(999, persona())))).estado).toBe(404);
    expect((await falla(w(empleados.eliminar(999)))).estado).toBe(404);
  });

  it('crear distribuidor devuelve {id, codigo} con la forma DIS-XXXXXX (RN-15), listado y categoría', async () => {
    const { id, codigo } = await w(
      distribuidores.crear({
        nombre: 'Nuevo Dist',
        documento: '800111222',
        correo: 'nuevo@dist.co',
        telefono: '6011112222',
      }),
    );
    expect(codigo).toMatch(/^DIS-[A-Z0-9]{6}$/);
    const d = await w(distribuidores.detalle(id));
    expect(d.campos).toEqual(
      expect.arrayContaining([`codigo: ${codigo}`, 'categoria: Básica', 'referidos: 0']),
    );
    expect((await w(distribuidores.listar('nuevo dist')))[0].subtitulo).toContain(codigo);
  });

  it('el distribuidor sembrado con más de 100 referidos es Premium (RN-19)', async () => {
    const a = (await w(distribuidores.listar('andes')))[0];
    const d = await w(distribuidores.detalle(a.id));
    expect(d.campos).toContain('categoria: Premium');
  });

  it('un distribuidor dado de baja deja de servir como código de referido (RN-13)', async () => {
    const { id, codigo } = await w(
      distribuidores.crear({
        nombre: 'Temp',
        documento: '700111',
        correo: 'temp@dist.co',
        telefono: '6011112222',
      }),
    );
    await w(distribuidores.eliminar(id));
    const { distribuidorActivoPorCodigo } = await import('./gestion.estado');
    expect(distribuidorActivoPorCodigo(codigo)).toBeUndefined();
    expect(distribuidorActivoPorCodigo('DIS-ANDES1')?.activo).toBe(true);
  });

  it('consultas CLIENTE: listado con filtro y detalle; 404 si no existe', async () => {
    const lista = await w(consultas.basico('CLIENTE'));
    expect(lista.length).toBeGreaterThanOrEqual(4);
    expect((await w(consultas.basico('CLIENTE', 'hostaliza')))[0].titulo).toBe('Hostal Iza');
    const d = await w(consultas.detalle('CLIENTE', lista[0].id));
    expect(d.campos.some((c) => c.startsWith('sitio: '))).toBe(true);
    expect((await falla(w(consultas.detalle('CLIENTE', 9999)))).estado).toBe(404);
  });

  it('403 si la sesión no tiene la operación; 401 sin sesión', async () => {
    fijarUsuarioSimulado('soporte');
    const e = await falla(w(empleados.listar()));
    expect(e).toMatchObject({ estado: 403, codigo: 'SIN_PERMISO' });
    fijarUsuarioSimulado('anonimo');
    expect((await falla(w(distribuidores.listar()))).estado).toBe(401);
  });

  it('503 CONTINGENCIA en escrituras cuando la falla está forzada', async () => {
    localStorage.setItem('chibchaweb.simulado.falla', 'contingencia');
    try {
      expect((await falla(w(empleados.crear(persona())))).codigo).toBe('CONTINGENCIA');
      expect((await falla(w(empleados.eliminar(1)))).estado).toBe(503);
    } finally {
      localStorage.removeItem('chibchaweb.simulado.falla');
    }
  });
});
