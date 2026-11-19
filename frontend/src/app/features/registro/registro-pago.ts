import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ErroresCampo } from '../../shared/errores-formulario';
import { CamposPago } from '../../shared/formularios/campos-pago';
import { crearFormPago, formatearNumero, leerPago } from '../../shared/formularios/pago';
import { CabeceraPaso } from './cabecera-paso';
import { PasoRegistro, RegistroStore } from './registro.store';

/** M-04 · Registro, paso 3: dirección de facturación y tarjeta; *Crear cuenta*. */
@Component({
  selector: 'app-registro-pago',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CabeceraPaso, CamposPago, ReactiveFormsModule],
  template: `
    <app-cabecera-paso
      [paso]="3"
      titulo="Dirección y medio de pago"
      subtitulo="Validamos la dirección y la tarjeta antes de guardarlas."
    />
    <form class="tarjeta" [formGroup]="form" (ngSubmit)="crear()" novalidate>
      @if (aviso(); as a) {
        <p class="aviso error" role="alert"><span aria-hidden="true">⚠️</span> {{ a }}</p>
      }
      <app-campos-pago [form]="form" [errores]="errores.errores()" />
      <div class="acciones">
        <button type="button" class="boton secundario" (click)="volver()">Volver</button>
        <button type="submit" class="boton" [disabled]="store.enviando()">
          {{ store.enviando() ? 'Creando cuenta…' : 'Crear cuenta' }}
        </button>
      </div>
    </form>
  `,
  styles: `
    .aviso {
      margin-bottom: 24px;
    }
    .acciones {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 28px;
    }
  `,
})
export class RegistroPago {
  protected readonly store = inject(RegistroStore);
  private readonly router = inject(Router);

  protected readonly form = crearFormPago();
  protected readonly errores = new ErroresCampo([this.form]);
  protected readonly aviso = signal<string | null>(null);

  constructor() {
    const previo = this.store.pago();
    if (previo) {
      this.form.patchValue({
        ...previo,
        numeroTarjeta: formatearNumero(previo.numeroTarjeta),
        vencimiento: previo.vencimiento
          ? `${previo.vencimiento.slice(5, 7)}/${previo.vencimiento.slice(2, 4)}`
          : '',
      });
    } else {
      // Mismo domicilio que la residencia por defecto (se puede cambiar).
      const d = this.store.datos();
      if (d) {
        this.form.patchValue({
          lineaFacturacion: d.lineaResidencia,
          ciudadFacturacion: d.ciudadResidencia,
          codigoPostalFacturacion: d.codigoPostalResidencia,
        });
      }
    }
    this.aplicarPendiente();
  }

  private aplicarPendiente(): void {
    const e = this.store.tomarError('pago');
    if (!e) return;
    if (e.campo) {
      this.errores.fijar(e.campo, e.mensaje);
      this.form.markAllAsTouched();
    }
    this.aviso.set(e.mensaje);
  }

  protected async crear(): Promise<void> {
    this.aviso.set(null);
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    const destino: 'ok' | PasoRegistro = await this.store.crear(leerPago(this.form));
    if (destino === 'ok') {
      await this.router.navigateByUrl('/cliente');
    } else if (destino === 'pago') {
      this.aplicarPendiente();
      const general = this.store.errorGeneral();
      if (general) this.aviso.set(general);
    } else {
      await this.router.navigateByUrl(`/registro/${destino}`);
    }
  }

  protected volver(): void {
    const { codigoSeguridad, ...resto } = leerPago(this.form);
    void codigoSeguridad; // el código de seguridad no se conserva
    this.store.pago.set(resto);
    void this.router.navigateByUrl('/registro/plan');
  }
}
