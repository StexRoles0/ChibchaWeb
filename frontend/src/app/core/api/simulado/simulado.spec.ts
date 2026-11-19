import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { DatosClienteDTO } from '../dto';
import { reiniciarSimulado } from './almacen';
import { simuladoInterceptor } from './simulado.interceptor';
import { fijarUsuarioSimulado } from './sesiones';
import { erroresInterceptor } from '../../interceptores';

const B = '/api/v1';
const registro = (o: Partial<DatosClienteDTO> = {}): DatosClienteDTO => ({
  nombre: 'Laura Gómez',
  telefono: '3001234567',
  lineaResidencia: 'Calle 1 # 2-3',
  ciudadResidencia: 'Sogamoso',
  codigoPostalResidencia: '152210',
  sitio: 'tiendalaura',
  plataforma: 'UNIX',
  idPaquete: 2,
  idPlan: 3,
  lineaFacturacion: 'Calle 1 # 2-3',
  ciudadFacturacion: 'Sogamoso',
  codigoPostalFacturacion: '152210',
  numeroTarjeta: '4111111111111111',
  vencimiento: '2030-08-01',
  codigoSeguridad: '123',
  franquicia: 'VISA',
  ...o,
});

describe('modo simulado', () => {
  let http: HttpClient;
  const get = <T>(u: string) => firstValueFrom(http.get<T>(B + u));
  const post = <T>(u: string, b: unknown = {}) => firstValueFrom(http.post<T>(B + u, b));
  const falla = async (p: Promise<unknown>) => {
    try {
      await p;
    } catch (e) {
      return e as { estado: number; codigo: string; campo?: string; mensaje: string };
    }
    throw new Error('debía fallar');
  };
  /** Entra por el flujo real: inicio → callback con el `state` devuelto. */
  async function entrar(correo: string) {
    const { url } = await get<{ url: string }>(`/auth/oauth/inicio?correo=${correo}`);
    const q = new URL(url, 'http://x').searchParams;
    return post<{ registrado: boolean; tipoUsuario: string; rol?: string }>(
      '/auth/oauth/callback',
      {
        codigo: q.get('code'),
        estado: q.get('state'),
      },
    );
  }

  beforeEach(() => {
    reiniciarSimulado();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([
          { path: 'acceso', children: [] },
          { path: 'no-autorizado', children: [] },
        ]),
        provideHttpClient(withInterceptors([erroresInterceptor, simuladoInterceptor])),
      ],
    });
    http = TestBed.inject(HttpClient);
  });

  it('sin sesión: 401; el inicio exige correo (400) y arma la URL dev:', async () => {
    expect((await falla(get('/auth/sesion'))).estado).toBe(401);
    expect((await falla(get('/auth/oauth/inicio'))).codigo).toBe('SOLICITUD_INVALIDA');
    const { url } = await get<{ url: string }>('/auth/oauth/inicio?correo=a@b.co');
    expect(url).toMatch(/^\/auth\/callback\?code=dev:a%40b\.co&state=\w+$/);
  });

  it('callback: empleado sembrado, cliente sembrado y correo nuevo (sin registrar)', async () => {
    expect(await entrar('soporte@chibchaweb.co')).toMatchObject({ rol: 'Soporte' });
    expect(await entrar('steven@correo.co')).toMatchObject({ tipoUsuario: 'CLIENTE' });
    expect(await entrar('laura.gomez@correo.co')).toMatchObject({
      registrado: false,
      nombre: 'Laura Gomez',
    });
  });

  it('callback: estado distinto → 401 AUTORIZACION_FALLIDA; inactivo → 403 USUARIO_INACTIVO', async () => {
    await get('/auth/oauth/inicio?correo=a@b.co');
    const e = await falla(post('/auth/oauth/callback', { codigo: 'dev:a@b.co', estado: 'otro' }));
    expect(e).toMatchObject({ estado: 401, codigo: 'AUTORIZACION_FALLIDA' });
    expect(await falla(entrar('inactivo@correo.co'))).toMatchObject({
      estado: 403,
      codigo: 'USUARIO_INACTIVO',
    });
  });

  it('catálogo con el formato del contrato', async () => {
    const paquetes = await get<{ subtitulo: string }[]>('/catalogo/paquetes');
    const planes = await get<{ subtitulo: string }[]>('/catalogo/planes');
    expect(paquetes.map((p) => p.subtitulo)).toEqual(['5.00', '10.00', '20.00']);
    expect(planes.map((p) => p.subtitulo)).toEqual(['1|0.00', '3|0.05', '6|0.10', '12|0.15']);
  });

  describe('POST /auth/registro', () => {
    beforeEach(async () => {
      await entrar('laura@correo.co');
    });

    it('crea la cuenta, abre la sesión y deja el detalle consultable', async () => {
      const r = await post<{ registrado: boolean; correo: string }>('/auth/registro', registro());
      expect(r).toMatchObject({ registrado: true, correo: 'laura@correo.co' });
      const d = await get<{ campos: string[] }>('/clientes/me');
      expect(d.campos).toContain('sitio: tiendalaura.chibchaweb.com');
      expect(d.campos).toContain('tarjeta: VISA •••• 1111');
      expect(d.campos).toContain('montoPeriodo: 54.00');
    });

    it('tarjeta terminada en 0002: 422 del validador en numeroTarjeta', async () => {
      const e = await falla(
        post('/auth/registro', registro({ numeroTarjeta: '4111111111110002' })),
      );
      expect(e).toMatchObject({ estado: 422, campo: 'numeroTarjeta' });
      expect(e.mensaje).toContain('rechazada por el verificador');
    });

    it('número que no cumple el patrón de la franquicia, tarjeta vencida y CVV inválido', async () => {
      expect((await falla(post('/auth/registro', registro({ franquicia: 'DINERS' })))).campo).toBe(
        'numeroTarjeta',
      );
      expect(
        (await falla(post('/auth/registro', registro({ vencimiento: '2020-01-01' })))).campo,
      ).toBe('vencimiento');
      expect((await falla(post('/auth/registro', registro({ codigoSeguridad: '12' })))).campo).toBe(
        'codigoSeguridad',
      );
    });

    it('subdominio ocupado: 409 SUBDOMINIO_EN_USO; distribuidor desconocido: 422', async () => {
      expect(
        await falla(post('/auth/registro', registro({ sitio: 'cafedeboyaca' }))),
      ).toMatchObject({ estado: 409, codigo: 'SUBDOMINIO_EN_USO' });
      expect(
        await falla(post('/auth/registro', registro({ codigoDistribuidor: 'DIS-NOEXISTE' }))),
      ).toMatchObject({ estado: 422, campo: 'codigoDistribuidor' });
      const ok = await post<{ registrado: boolean }>(
        '/auth/registro',
        registro({ codigoDistribuidor: 'DIS-ANDES1' }),
      );
      expect(ok.registrado).toBe(true);
    });

    it('sitio "contingencia" responde 503 CONTINGENCIA', async () => {
      expect(
        await falla(post('/auth/registro', registro({ sitio: 'contingencia' }))),
      ).toMatchObject({
        estado: 503,
        codigo: 'CONTINGENCIA',
      });
    });
  });

  describe('/clientes/me', () => {
    beforeEach(async () => {
      await entrar('steven@correo.co');
    });

    it('GET devuelve las claves fijas del DetalleDTO de CLIENTE', async () => {
      const d = await get<{ campos: string[] }>('/clientes/me');
      const claves = d.campos.map((c) => c.split(':')[0]);
      expect(claves).toEqual([
        'nombre',
        'correo',
        'telefono',
        'lineaResidencia',
        'ciudadResidencia',
        'codigoPostalResidencia',
        'lineaFacturacion',
        'ciudadFacturacion',
        'codigoPostalFacturacion',
        'tarjeta',
        'franquicia',
        'vencimiento',
        'idSuscripcion',
        'sitio',
        'plataforma',
        'idPaquete',
        'paquete',
        'idPlan',
        'plan',
        'montoPeriodo',
        'fechaCorte',
        'distribuidor',
        'activo',
      ]);
    });

    it('PATCH por categoría: PERSONAL, PAQUETE_PLAN y PAGO (204)', async () => {
      const patch = (cat: string, b: unknown) =>
        firstValueFrom(http.patch(`${B}/clientes/me?categoria=${cat}`, b));
      await patch('PERSONAL', registro({ telefono: '3105550198', sitio: 'cafedeboyaca' }));
      await patch('PAQUETE_PLAN', { idSuscripcion: 1, idPaquete: 1, idPlan: 1 });
      await patch(
        'PAGO',
        registro({ numeroTarjeta: '5105105105105100', franquicia: 'MASTERCARD' }),
      );
      const campos = (await get<{ campos: string[] }>('/clientes/me')).campos;
      expect(campos).toContain('telefono: 3105550198');
      expect(campos).toContain('paquete: Chibcha-Plata');
      expect(campos).toContain('montoPeriodo: 5.00');
      expect(campos).toContain('tarjeta: MASTERCARD •••• 5100');
    });

    it('PATCH PAGO con tarjeta 0002 → 422; PERSONAL con sitio de otro → 409', async () => {
      const e = await falla(
        firstValueFrom(
          http.patch(
            `${B}/clientes/me?categoria=PAGO`,
            registro({ numeroTarjeta: '4111111111110002' }),
          ),
        ),
      );
      expect(e).toMatchObject({ estado: 422, campo: 'numeroTarjeta' });
      const e2 = await falla(
        firstValueFrom(
          http.patch(`${B}/clientes/me?categoria=PERSONAL`, registro({ sitio: 'www' })),
        ),
      );
      expect(e2.codigo).toBe('SUBDOMINIO_EN_USO');
    });

    it('DELETE: 204, cierra la sesión y el correo ya no puede entrar (403)', async () => {
      await firstValueFrom(http.delete(`${B}/clientes/me`));
      expect((await falla(get('/auth/sesion'))).estado).toBe(401);
      expect((await falla(entrar('steven@correo.co'))).codigo).toBe('USUARIO_INACTIVO');
    });

    it('un empleado no es cliente: /clientes/me responde 401 sin sesión de cliente', async () => {
      fijarUsuarioSimulado('anonimo');
      expect((await falla(get('/clientes/me'))).estado).toBe(401);
    });
  });
});
