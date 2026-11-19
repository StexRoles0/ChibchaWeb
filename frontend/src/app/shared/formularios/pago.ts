import {
  AbstractControl,
  FormControl,
  FormGroup,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { DatosClienteDTO } from '../../core/api/dto';
import { codigoPostal, noVacio } from './validadores';

export type Franquicia = DatosClienteDTO['franquicia'];

/** Mismos patrones que `franquicia.patron_numero` del seed. */
export const PATRONES: Record<Franquicia, RegExp> = {
  VISA: /^4[0-9]{12}([0-9]{3})?$/,
  MASTERCARD: /^(5[1-5][0-9]{14}|2[2-7][0-9]{14})$/,
  DINERS: /^3(0[0-5]|[68][0-9])[0-9]{11}$/,
};

export const FRANQUICIAS: { valor: Franquicia; etiqueta: string }[] = [
  { valor: 'VISA', etiqueta: 'VISA' },
  { valor: 'MASTERCARD', etiqueta: 'MasterCard' },
  { valor: 'DINERS', etiqueta: 'Diners Club' },
];

export const soloDigitos = (v: string): string => v.replace(/\D/g, '');

/** Detecta la franquicia por los primeros dígitos, mientras se escribe. */
export function detectarFranquicia(numero: string): Franquicia | null {
  const d = soloDigitos(numero);
  if (/^4/.test(d)) return 'VISA';
  if (/^(5[1-5]|2[2-7])/.test(d)) return 'MASTERCARD';
  if (/^(30[0-5]|3[68])/.test(d)) return 'DINERS';
  return null;
}

/** 4111111111111111 → "4111 1111 1111 1111" (máximo 19 dígitos). */
export function formatearNumero(v: string): string {
  return (
    soloDigitos(v)
      .slice(0, 19)
      .match(/.{1,4}/g) ?? []
  ).join(' ');
}

/** "0828" → "08/28" */
export function formatearVencimiento(v: string): string {
  const d = soloDigitos(v).slice(0, 4);
  return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
}

/** "08/28" → "2028-08-01" (se envía AAAA-MM-01). */
export function vencimientoAIso(v: string): string {
  const m = /^(\d{2})\/(\d{2})$/.exec(v.trim());
  return m ? `20${m[2]}-${m[1]}-01` : '';
}

const franquiciaDe = (c: AbstractControl): Franquicia =>
  (c.parent?.get('franquicia')?.value as Franquicia | undefined) ?? 'VISA';

function validarNumero(c: AbstractControl): ValidationErrors | null {
  const d = soloDigitos(String(c.value ?? ''));
  if (d === '') return null;
  const f = franquiciaDe(c);
  return PATRONES[f].test(d)
    ? null
    : { numero: { mensaje: `El número no corresponde a una tarjeta ${f} válida.` } };
}

/** Vigente: vencimiento ≥ primer día del mes actual (RN-11 b). */
export function validarVencimiento(c: AbstractControl, hoy = new Date()): ValidationErrors | null {
  const v = String(c.value ?? '').trim();
  if (v === '') return null;
  const m = /^(0[1-9]|1[0-2])\/(\d{2})$/.exec(v);
  if (!m) return { formato: { mensaje: 'Escribe el vencimiento como MM/AA.' } };
  const anio = 2000 + Number(m[2]);
  const mes = Number(m[1]);
  const vigente =
    anio > hoy.getFullYear() || (anio === hoy.getFullYear() && mes >= hoy.getMonth() + 1);
  return vigente ? null : { vencida: { mensaje: 'La tarjeta está vencida.' } };
}

function validarCodigo(c: AbstractControl): ValidationErrors | null {
  const v = String(c.value ?? '');
  return v === '' || /^\d{3,4}$/.test(v)
    ? null
    : { codigo: { mensaje: 'El código de seguridad tiene 3 o 4 dígitos.' } };
}

export function crearFormPago() {
  const req = [Validators.required, noVacio];
  const form = new FormGroup({
    lineaFacturacion: new FormControl('', { nonNullable: true, validators: req }),
    ciudadFacturacion: new FormControl('', { nonNullable: true, validators: req }),
    codigoPostalFacturacion: new FormControl('', {
      nonNullable: true,
      validators: [...req, codigoPostal],
    }),
    franquicia: new FormControl<string>('VISA', { nonNullable: true, validators: req }),
    numeroTarjeta: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, validarNumero],
    }),
    vencimiento: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, validarVencimiento],
    }),
    codigoSeguridad: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, validarCodigo],
    }),
  });

  // El número se escribe con espacios y detecta la franquicia.
  form.controls.numeroTarjeta.valueChanges.subscribe((v) => {
    const f = formatearNumero(v);
    if (f !== v) form.controls.numeroTarjeta.setValue(f, { emitEvent: false });
    const detectada = detectarFranquicia(f);
    if (detectada && detectada !== form.controls.franquicia.value) {
      form.controls.franquicia.setValue(detectada);
    }
  });
  form.controls.franquicia.valueChanges.subscribe(() =>
    form.controls.numeroTarjeta.updateValueAndValidity({ emitEvent: false }),
  );
  form.controls.vencimiento.valueChanges.subscribe((v) => {
    const f = formatearVencimiento(v);
    if (f !== v) form.controls.vencimiento.setValue(f, { emitEvent: false });
  });
  return form;
}

export type FormPago = ReturnType<typeof crearFormPago>;

export type BloquePago = Pick<
  DatosClienteDTO,
  | 'lineaFacturacion'
  | 'ciudadFacturacion'
  | 'codigoPostalFacturacion'
  | 'numeroTarjeta'
  | 'vencimiento'
  | 'codigoSeguridad'
  | 'franquicia'
>;

/** Bloque PAGO listo para el contrato (número sin espacios, vencimiento AAAA-MM-01). */
export function leerPago(form: FormPago): BloquePago {
  const v = form.getRawValue();
  return {
    lineaFacturacion: v.lineaFacturacion.trim(),
    ciudadFacturacion: v.ciudadFacturacion.trim(),
    codigoPostalFacturacion: v.codigoPostalFacturacion.trim(),
    numeroTarjeta: soloDigitos(v.numeroTarjeta),
    vencimiento: vencimientoAIso(v.vencimiento),
    codigoSeguridad: v.codigoSeguridad,
    franquicia: v.franquicia as Franquicia,
  };
}
