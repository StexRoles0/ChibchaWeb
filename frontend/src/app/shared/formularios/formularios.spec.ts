import { FormControl } from '@angular/forms';
import {
  crearFormPago,
  detectarFranquicia,
  formatearNumero,
  formatearVencimiento,
  leerPago,
  validarVencimiento,
  vencimientoAIso,
} from './pago';
import { crearFormPersonal, leerPersonal } from './personal';
import { codigoPostal, nombreSitio, telefono } from './validadores';

const c = (v: string) => new FormControl(v);

describe('validadores', () => {
  it('código postal alfanumérico de 4 a 10 caracteres (RN-10)', () => {
    expect(codigoPostal(c('152210'))).toBeNull();
    expect(codigoPostal(c('123'))).not.toBeNull();
    expect(codigoPostal(c('12345678901'))).not.toBeNull();
    expect(codigoPostal(c('12 45'))).not.toBeNull();
  });

  it('nombre del sitio: 63 caracteres, sin guion al inicio ni al final', () => {
    expect(nombreSitio(c('cafedeboyaca'))).toBeNull();
    expect(nombreSitio(c('mi-sitio-2'))).toBeNull();
    expect(nombreSitio(c('-sitio'))).not.toBeNull();
    expect(nombreSitio(c('sitio-'))).not.toBeNull();
    expect(nombreSitio(c('mi sitio'))).not.toBeNull();
    expect(nombreSitio(c('a'.repeat(63)))).toBeNull();
    expect(nombreSitio(c('a'.repeat(64)))).not.toBeNull();
  });

  it('teléfono de 7 a 15 dígitos', () => {
    expect(telefono(c('300 412 5587'))).toBeNull();
    expect(telefono(c('+57 (601) 555-6677'))).toBeNull();
    expect(telefono(c('12345'))).not.toBeNull();
    expect(telefono(c('abc1234567'))).not.toBeNull();
  });
});

describe('formulario de datos personales', () => {
  it('es inválido vacío y obliga los campos del contrato', () => {
    const f = crearFormPersonal();
    expect(f.invalid).toBe(true);
    expect(f.controls.nombre.hasError('required')).toBe(true);
    expect(f.controls.codigoDistribuidor.valid).toBe(true);
  });

  it('arma el bloque sin el código de distribuidor si no se pide o está vacío', () => {
    const f = crearFormPersonal();
    f.patchValue({
      nombre: ' Laura Gómez ',
      telefono: '3001234567',
      lineaResidencia: 'Calle 1 # 2-3',
      ciudadResidencia: 'Sogamoso',
      codigoPostalResidencia: '152210',
      sitio: 'CafeDeBoyaca',
      codigoDistribuidor: ' dis-andes1 ',
    });
    expect(f.valid).toBe(true);
    const sin = leerPersonal(f, false);
    expect(sin.codigoDistribuidor).toBeUndefined();
    expect(sin.sitio).toBe('cafedeboyaca');
    expect(sin.nombre).toBe('Laura Gómez');
    expect(leerPersonal(f, true).codigoDistribuidor).toBe('DIS-ANDES1');
  });
});

describe('tarjeta', () => {
  it('detecta la franquicia con los patrones del seed', () => {
    expect(detectarFranquicia('4111 1111')).toBe('VISA');
    expect(detectarFranquicia('5105')).toBe('MASTERCARD');
    expect(detectarFranquicia('2221')).toBe('MASTERCARD');
    expect(detectarFranquicia('3056')).toBe('DINERS');
    expect(detectarFranquicia('9999')).toBeNull();
  });

  it('formatea número y vencimiento mientras se escribe', () => {
    expect(formatearNumero('4111111111111111')).toBe('4111 1111 1111 1111');
    expect(formatearNumero('41 1a')).toBe('411');
    expect(formatearVencimiento('0828')).toBe('08/28');
    expect(formatearVencimiento('08')).toBe('08');
    expect(vencimientoAIso('08/28')).toBe('2028-08-01');
    expect(vencimientoAIso('8/28')).toBe('');
  });

  it('el vencimiento debe estar vigente (≥ primer día del mes actual)', () => {
    const hoy = new Date(2026, 10, 16); // noviembre de 2026
    expect(validarVencimiento(c('11/26'), hoy)).toBeNull();
    expect(validarVencimiento(c('10/26'), hoy)).toMatchObject({ vencida: expect.anything() });
    expect(validarVencimiento(c('13/30'), hoy)).toMatchObject({ formato: expect.anything() });
    expect(validarVencimiento(c('08/28'), hoy)).toBeNull();
  });

  it('el formulario de pago detecta la franquicia, valida el número y envía AAAA-MM-01', () => {
    const f = crearFormPago();
    f.controls.numeroTarjeta.setValue('4111111111111111');
    expect(f.controls.numeroTarjeta.value).toBe('4111 1111 1111 1111');
    expect(f.controls.franquicia.value).toBe('VISA');
    expect(f.controls.numeroTarjeta.valid).toBe(true);

    // Cambiar a MasterCard a mano invalida el número VISA.
    f.controls.franquicia.setValue('MASTERCARD');
    expect(f.controls.numeroTarjeta.errors).toMatchObject({
      numero: { mensaje: 'El número no corresponde a una tarjeta MASTERCARD válida.' },
    });

    f.controls.franquicia.setValue('VISA');
    f.patchValue({
      lineaFacturacion: 'Calle 24 # 7-31',
      ciudadFacturacion: 'Sogamoso',
      codigoPostalFacturacion: '152210',
      vencimiento: '0830',
      codigoSeguridad: '123',
    });
    expect(f.valid).toBe(true);
    expect(leerPago(f)).toMatchObject({
      numeroTarjeta: '4111111111111111',
      vencimiento: '2030-08-01',
      codigoSeguridad: '123',
      franquicia: 'VISA',
    });
  });

  it('el código de seguridad admite 3 o 4 dígitos (P-11)', () => {
    const f = crearFormPago();
    f.controls.codigoSeguridad.setValue('12');
    expect(f.controls.codigoSeguridad.invalid).toBe(true);
    f.controls.codigoSeguridad.setValue('12345');
    expect(f.controls.codigoSeguridad.invalid).toBe(true);
    f.controls.codigoSeguridad.setValue('123');
    expect(f.controls.codigoSeguridad.valid).toBe(true);
    f.controls.codigoSeguridad.setValue('1234');
    expect(f.controls.codigoSeguridad.valid).toBe(true);
  });
});
