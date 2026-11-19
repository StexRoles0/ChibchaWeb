import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

/** Validador por expresión regular que trae su propio mensaje. */
export function patron(re: RegExp, mensaje: string, clave = 'patron'): ValidatorFn {
  return (c: AbstractControl): ValidationErrors | null => {
    const v = String(c.value ?? '').trim();
    return v === '' || re.test(v) ? null : { [clave]: { mensaje } };
  };
}

/** Código postal alfanumérico de 4 a 10 caracteres (RN-10). */
export const codigoPostal = patron(
  /^[A-Za-z0-9]{4,10}$/,
  'El código postal es alfanumérico, de 4 a 10 caracteres.',
  'codigoPostal',
);

/** Teléfono: de 7 a 15 dígitos; se aceptan espacios, +, paréntesis y guiones. */
export const telefono: ValidatorFn = (c) => {
  const v = String(c.value ?? '').trim();
  if (v === '') return null;
  const digitos = v.replace(/\D/g, '').length;
  return /^[0-9 +()-]+$/.test(v) && digitos >= 7 && digitos <= 15
    ? null
    : { telefono: { mensaje: 'Escribe un teléfono de 7 a 15 dígitos.' } };
};

/** Nombre del sitio: 1 a 63 caracteres, letras, dígitos y guiones, sin guion al inicio ni al final. */
export const nombreSitio: ValidatorFn = (c) => {
  const v = String(c.value ?? '').trim();
  if (v === '') return null;
  if (v.length > 63) return { sitio: { mensaje: 'El sitio admite hasta 63 caracteres.' } };
  return /^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$/.test(v)
    ? null
    : { sitio: { mensaje: 'Usa letras, números y guiones, sin guion al inicio ni al final.' } };
};

/** Un valor con solo espacios no cuenta como lleno. */
export const noVacio: ValidatorFn = (c) =>
  String(c.value ?? '').trim() === '' && c.value !== '' ? { required: true } : null;

/** RN-16: nombre de dominio de 1 a 63 caracteres, letras, dígitos y guiones, sin guion al inicio ni al final. */
export const nombreDominio: ValidatorFn = (c) => {
  const v = String(c.value ?? '').trim();
  if (v === '') return null;
  if (v.length > 63) return { dominio: { mensaje: 'El nombre admite hasta 63 caracteres.' } };
  return /^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$/.test(v)
    ? null
    : {
        dominio: {
          mensaje: 'Usa letras, números y guiones, sin guion al inicio ni al final.',
        },
      };
};
