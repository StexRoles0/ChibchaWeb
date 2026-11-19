import { DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormGroup } from '@angular/forms';
import { ErrorApi } from '../core/errores';

/**
 * Errores 422 por campo: guarda el mensaje del servidor bajo el nombre del campo y lo
 * borra cuando el usuario edita ese campo. Se crea dentro de un contexto de inyección.
 */
export class ErroresCampo {
  private readonly _errores = signal<Record<string, string>>({});
  readonly errores = this._errores.asReadonly();

  constructor(
    grupos: FormGroup[],
    private readonly destroyRef = inject(DestroyRef),
  ) {
    for (const g of grupos) {
      for (const [nombre, control] of Object.entries(g.controls)) {
        this.vigilar(nombre, control);
      }
    }
  }

  private vigilar(nombre: string, control: AbstractControl): void {
    control.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      if (this._errores()[nombre]) this.quitar(nombre);
    });
  }

  de(campo: string): string | null {
    return this._errores()[campo] ?? null;
  }

  fijar(campo: string, mensaje: string): void {
    this._errores.update((e) => ({ ...e, [campo]: mensaje }));
  }

  quitar(campo: string): void {
    this._errores.update((e) => {
      const { [campo]: _quitado, ...resto } = e;
      void _quitado;
      return resto;
    });
  }

  limpiar(): void {
    this._errores.set({});
  }
}

/** El backend nombra `subdominio` al campo que el formulario llama `sitio`. */
const ALIAS_CAMPO: Record<string, string> = { subdominio: 'sitio' };

/** Campo al que apunta un error de servidor; SUBDOMINIO_EN_USO es siempre del campo `sitio`. */
export function campoDelError(error: ErrorApi): string | undefined {
  if (error.codigo === 'SUBDOMINIO_EN_USO') return 'sitio';
  if (error.estado === 422 || error.codigo === 'DUPLICADO') {
    return error.campo ? (ALIAS_CAMPO[error.campo] ?? error.campo) : undefined;
  }
  return undefined;
}
