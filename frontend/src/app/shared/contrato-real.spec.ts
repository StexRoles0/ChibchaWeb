import { TestBed } from '@angular/core/testing';
import { ContingenciaStore } from '../core/contingencia.store';
import { CATEGORIAS_TICKET, etiquetaCategoria } from './categoria-ticket';
import { campoDelError } from './errores-formulario';
import { etiquetaEvento } from './evento-respaldo';

describe('formas del backend real', () => {
  it('traduce el literal de la categoría de ticket a su etiqueta', () => {
    expect(CATEGORIAS_TICKET.map((c) => c.valor)).toEqual([
      'RENDIMIENTO',
      'CORREO',
      'BASE_DATOS',
      'DOMINIO',
      'OTRA',
    ]);
    expect(etiquetaCategoria('BASE_DATOS')).toBe('Base de datos');
    expect(etiquetaCategoria('RENDIMIENTO')).toBe('Rendimiento');
    expect(etiquetaCategoria('NUEVA_CATEGORIA')).toBe('Nueva categoria');
  });

  it('traduce los tipos técnicos de los eventos respaldados', () => {
    expect(etiquetaEvento('Suscripcion.registrar_pago')).toBe('Suscripción · registro de pago');
    expect(etiquetaEvento('Comision.registrar_cheque')).toBe('Comisión · registro de cheque');
    expect(etiquetaEvento('SolicitudDominio.insertar')).toBe('Solicitud de dominio · creación');
    expect(etiquetaEvento('Usuario.actualizar')).toBe('Usuario · modificación');
    expect(etiquetaEvento('(formato inválido)')).toBe('(formato inválido)');
  });

  it('el campo `subdominio` del backend es el campo `sitio` del formulario', () => {
    expect(
      campoDelError({
        codigo: 'SUBDOMINIO_EN_USO',
        estado: 409,
        campo: 'subdominio',
        mensaje: 'x',
      }),
    ).toBe('sitio');
    expect(
      campoDelError({ codigo: 'VALIDACION', estado: 422, campo: 'subdominio', mensaje: 'x' }),
    ).toBe('sitio');
    expect(
      campoDelError({ codigo: 'VALIDACION', estado: 422, campo: 'lineaResidencia', mensaje: 'x' }),
    ).toBe('lineaResidencia');
  });

  it('el banner solo promete el respaldo si el servidor dice que la operación quedó respaldada', () => {
    const c = TestBed.inject(ContingenciaStore);
    c.activar('La operación quedó respaldada');
    expect(c.texto()).toContain('quedó respaldada');
    c.activar('La base de datos no está disponible; la consulta no se pudo realizar');
    expect(c.texto()).toBe(
      'El sistema está en modo contingencia: la base de datos no está disponible; la consulta no se pudo realizar.',
    );
    c.activar();
    expect(c.texto()).toContain('quedó respaldada');
  });
});
