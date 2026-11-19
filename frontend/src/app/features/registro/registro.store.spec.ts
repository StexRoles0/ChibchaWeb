import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, UrlTree } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AccesoApi } from '../../core/api/acceso.api';
import { USUARIOS_SIMULADOS } from '../../core/api/simulado/sesiones';
import { SesionStore } from '../../core/auth/sesion.store';
import { BloquePago } from '../../shared/formularios/pago';
import { datosCompletos, planCompleto } from './pasos.guardas';
import { pasoDeCampo, RegistroStore } from './registro.store';

const pago: BloquePago = {
  lineaFacturacion: 'Calle 1',
  ciudadFacturacion: 'Sogamoso',
  codigoPostalFacturacion: '152210',
  numeroTarjeta: '4111111111111111',
  vencimiento: '2030-08-01',
  codigoSeguridad: '123',
  franquicia: 'VISA',
};
const datos = {
  nombre: 'Laura',
  telefono: '3001234567',
  lineaResidencia: 'Calle 1',
  ciudadResidencia: 'Sogamoso',
  codigoPostalResidencia: '152210',
  sitio: 'tienda',
  plataforma: 'UNIX' as const,
  codigoDistribuidor: undefined,
};

function crear(api: Partial<AccesoApi>) {
  TestBed.configureTestingModule({
    providers: [provideRouter([]), RegistroStore, { provide: AccesoApi, useValue: api }],
  });
  return TestBed.inject(RegistroStore);
}
const err = (estado: number, codigo: string, mensaje: string, campo?: string) =>
  throwError(() => ({ estado, codigo, mensaje, campo }));

describe('RegistroStore', () => {
  it('ubica cada campo del contrato en su paso', () => {
    expect(pasoDeCampo('sitio')).toBe('datos');
    expect(pasoDeCampo('codigoDistribuidor')).toBe('datos');
    expect(pasoDeCampo('idPlan')).toBe('plan');
    expect(pasoDeCampo('numeroTarjeta')).toBe('pago');
    expect(pasoDeCampo(undefined)).toBe('pago');
  });

  it('carga el catálogo y lo convierte a números', async () => {
    const s = crear({
      paquetes: () => of([{ id: 2, titulo: 'Chibcha-Oro', subtitulo: '10.00', estado: '' }]),
      planes: () => of([{ id: 3, titulo: 'Semestral', subtitulo: '6|0.10', estado: '' }]),
    });
    await s.cargarCatalogo();
    expect(s.paquetes()[0].tarifaCentavos).toBe(1000);
    expect(s.planes()[0]).toMatchObject({ meses: 6, descuentoPuntosBasicos: 1000 });
  });

  it('arma el DatosClienteDTO sin correo ni código de distribuidor vacío', () => {
    const s = crear({});
    expect(s.armarDto(pago)).toBeNull();
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    const dto = s.armarDto(pago)!;
    expect(dto).toMatchObject({
      idPaquete: 2,
      idPlan: 3,
      sitio: 'tienda',
      numeroTarjeta: '4111111111111111',
    });
    expect('codigoDistribuidor' in dto).toBe(false);
    expect('correo' in dto).toBe(false);
  });

  it('crear: éxito abre la sesión y no conserva el código de seguridad', async () => {
    const registro = vi.fn(() => of({ ...USUARIOS_SIMULADOS.cliente! }));
    const s = crear({ registro });
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    expect(await s.crear(pago)).toBe('ok');
    expect(TestBed.inject(SesionStore).esCliente()).toBe(true);
    expect('codigoSeguridad' in s.pago()!).toBe(false);
    expect(registro).toHaveBeenCalledOnce();
  });

  it('crear: 422 de un campo de otro paso devuelve ese paso y deja el error pendiente', async () => {
    const s = crear({
      registro: () => err(422, 'VALIDACION', 'Código inexistente', 'codigoDistribuidor'),
    });
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    expect(await s.crear(pago)).toBe('datos');
    expect(s.tomarError('pago')).toBeNull();
    expect(s.tomarError('datos')).toMatchObject({ campo: 'codigoDistribuidor' });
    expect(s.tomarError('datos')).toBeNull();
  });

  it('crear: 409 SUBDOMINIO_EN_USO sin campo se marca en `sitio` (paso 1)', async () => {
    const s = crear({ registro: () => err(409, 'SUBDOMINIO_EN_USO', 'En uso') });
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    expect(await s.crear(pago)).toBe('datos');
    expect(s.errorPendiente()).toMatchObject({ campo: 'sitio', paso: 'datos' });
  });

  it('crear: tarjeta rechazada queda en el paso de pago', async () => {
    const s = crear({ registro: () => err(422, 'VALIDACION', 'Rechazada', 'numeroTarjeta') });
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    expect(await s.crear(pago)).toBe('pago');
    expect(s.tomarError('pago')).toMatchObject({ campo: 'numeroTarjeta', mensaje: 'Rechazada' });
    expect(s.enviando()).toBe(false);
  });

  it('crear: un error sin campo va al aviso general', async () => {
    const s = crear({ registro: () => err(400, 'SOLICITUD_INVALIDA', 'Mal formado') });
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    await s.crear(pago);
    expect(s.errorGeneral()).toBe('Mal formado');
  });

  it('crear: 503 CONTINGENCIA no marca campos (lo explica el banner)', async () => {
    const s = crear({ registro: () => err(503, 'CONTINGENCIA', 'Contingencia') });
    s.guardarDatos(datos);
    s.guardarPlan(2, 3);
    expect(await s.crear(pago)).toBe('pago');
    expect(s.errorPendiente()).toBeNull();
    expect(s.errorGeneral()).toBeNull();
  });

  it('guardas de pasos: M-03 y M-04 exigen los pasos previos', () => {
    const s = crear({});
    const ir = (g: typeof datosCompletos) => {
      const r = TestBed.runInInjectionContext(() => g({} as never, {} as never));
      return r instanceof UrlTree ? TestBed.inject(Router).serializeUrl(r) : r;
    };
    expect(ir(datosCompletos)).toBe('/registro/datos');
    expect(ir(planCompleto)).toBe('/registro/datos');
    s.guardarDatos(datos);
    expect(ir(datosCompletos)).toBe(true);
    expect(ir(planCompleto)).toBe('/registro/plan');
    s.guardarPlan(1, 1);
    expect(ir(planCompleto)).toBe(true);
  });
});
