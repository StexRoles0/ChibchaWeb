import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SesionStore } from '../../core/auth/sesion.store';
import { ErroresCampo } from '../../shared/errores-formulario';
import { CamposPersonales } from '../../shared/formularios/campos-personales';
import { crearFormPersonal, leerPersonal } from '../../shared/formularios/personal';
import { CabeceraPaso } from './cabecera-paso';
import { RegistroStore } from './registro.store';

/** M-02 · Registro, paso 1: datos (CU-AUTH-03). */
@Component({
  selector: 'app-registro-datos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CabeceraPaso, CamposPersonales, ReactiveFormsModule],
  template: `
    <app-cabecera-paso
      [paso]="1"
      titulo="Crea tu cuenta"
      subtitulo="Tu nombre y correo llegan verificados del proveedor externo. Completa el resto para continuar."
    />
    <form class="tarjeta" [formGroup]="form" (ngSubmit)="continuar()" novalidate>
      <app-campos-personales
        [form]="form"
        [correo]="correo"
        [conDistribuidor]="true"
        [errores]="errores.errores()"
      />
      <div class="acciones">
        <button type="button" class="boton secundario" (click)="volver()">Volver</button>
        <button type="submit" class="boton">Continuar</button>
      </div>
    </form>
  `,
  styles: `
    .acciones {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 28px;
    }
  `,
})
export class RegistroDatos {
  private readonly store = inject(RegistroStore);
  private readonly sesion = inject(SesionStore);
  private readonly router = inject(Router);

  protected readonly form = crearFormPersonal();
  protected readonly errores = new ErroresCampo([this.form]);
  protected readonly correo = this.sesion.sesion()?.correo ?? '';

  constructor() {
    const previo = this.store.datos();
    this.form.patchValue(
      previo
        ? { ...previo, codigoDistribuidor: previo.codigoDistribuidor ?? '' }
        : { nombre: this.sesion.nombre() },
    );
    const pendiente = this.store.tomarError('datos');
    if (pendiente?.campo) {
      this.errores.fijar(pendiente.campo, pendiente.mensaje);
      this.form.markAllAsTouched();
    }
  }

  protected continuar(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    this.store.guardarDatos(leerPersonal(this.form, true));
    void this.router.navigateByUrl('/registro/plan');
  }

  /** En el primer paso, *Volver* cancela el registro y regresa a M-01. */
  protected volver(): void {
    void this.store.cancelar();
  }
}
