import { FormControl, FormGroup, ValidatorFn, Validators } from '@angular/forms';
import { DatosClienteDTO } from '../../core/api/dto';
import { codigoPostal, nombreSitio, noVacio, telefono } from './validadores';

export function crearFormPersonal() {
  const texto = (...validators: ValidatorFn[]) =>
    new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, noVacio, ...validators],
    });
  return new FormGroup({
    nombre: texto(Validators.maxLength(120)),
    telefono: texto(telefono),
    lineaResidencia: texto(),
    ciudadResidencia: texto(),
    codigoPostalResidencia: texto(codigoPostal),
    sitio: texto(nombreSitio),
    plataforma: new FormControl('UNIX', { nonNullable: true, validators: [Validators.required] }),
    codigoDistribuidor: new FormControl('', { nonNullable: true }),
  });
}

export type FormPersonal = ReturnType<typeof crearFormPersonal>;

/** Bloque PERSONAL / datos del paso 1 listo para el contrato. */
export function leerPersonal(
  form: FormPersonal,
  conDistribuidor: boolean,
): Pick<
  DatosClienteDTO,
  | 'nombre'
  | 'telefono'
  | 'lineaResidencia'
  | 'ciudadResidencia'
  | 'codigoPostalResidencia'
  | 'sitio'
  | 'plataforma'
  | 'codigoDistribuidor'
> {
  const v = form.getRawValue();
  const datos = {
    nombre: v.nombre.trim(),
    telefono: v.telefono.trim(),
    lineaResidencia: v.lineaResidencia.trim(),
    ciudadResidencia: v.ciudadResidencia.trim(),
    codigoPostalResidencia: v.codigoPostalResidencia.trim(),
    sitio: v.sitio.trim().toLowerCase(),
    plataforma: v.plataforma as 'WINDOWS' | 'UNIX',
  } as ReturnType<typeof leerPersonal>;
  if (conDistribuidor && v.codigoDistribuidor.trim()) {
    datos.codigoDistribuidor = v.codigoDistribuidor.trim().toUpperCase();
  }
  return datos;
}

export const PLATAFORMAS = [
  { valor: 'UNIX', etiqueta: 'Unix' },
  { valor: 'WINDOWS', etiqueta: 'Windows' },
];
