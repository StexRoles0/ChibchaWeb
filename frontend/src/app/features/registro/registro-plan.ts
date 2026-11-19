import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { Router } from '@angular/router';
import { SelectorPaquetePlan } from '../../shared/selector-paquete-plan';
import { CabeceraPaso } from './cabecera-paso';
import { RegistroStore } from './registro.store';

/** M-03 · Registro, paso 2: paquete y plan, con el monto del periodo en vivo (RN-01). */
@Component({
  selector: 'app-registro-plan',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CabeceraPaso, SelectorPaquetePlan],
  template: `
    <app-cabecera-paso
      [paso]="2"
      titulo="Elige tu paquete y plan"
      subtitulo="Puedes cambiarlos después desde tu perfil."
    />
    @if (store.errorCatalogo(); as e) {
      <p class="aviso error" role="alert">{{ e }}</p>
      <button type="button" class="boton secundario" (click)="reintentar()">Reintentar</button>
    } @else if (!store.catalogoCargado()) {
      <p role="status">Cargando paquetes y planes…</p>
    } @else {
      <app-selector-paquete-plan
        [paquetes]="store.paquetes()"
        [planes]="store.planes()"
        [(idPaquete)]="idPaquete"
        [(idPlan)]="idPlan"
      />
      @if (intentoSinElegir()) {
        <p class="aviso error" role="alert">Elige un paquete y un plan de pago para continuar.</p>
      }
      <div class="acciones">
        <button type="button" class="boton secundario" (click)="volver()">Volver</button>
        <button type="button" class="boton" (click)="continuar()">Continuar</button>
      </div>
    }
  `,
  styles: `
    .acciones {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
    }
    .aviso {
      margin-top: 16px;
    }
  `,
})
export class RegistroPlan implements OnInit {
  protected readonly store = inject(RegistroStore);
  private readonly router = inject(Router);

  protected readonly idPaquete = signal<number | null>(this.store.plan()?.idPaquete ?? null);
  protected readonly idPlan = signal<number | null>(this.store.plan()?.idPlan ?? null);
  protected readonly intentoSinElegir = signal(false);

  ngOnInit(): void {
    void this.store.cargarCatalogo();
    // Un 422 sobre idPaquete/idPlan lleva aquí: se muestra en el aviso de arriba.
    const e = this.store.tomarError('plan');
    if (e) this.intentoSinElegir.set(true);
  }

  protected reintentar(): void {
    void this.store.cargarCatalogo();
  }

  protected continuar(): void {
    const paquete = this.idPaquete();
    const plan = this.idPlan();
    if (paquete === null || plan === null) {
      this.intentoSinElegir.set(true);
      return;
    }
    this.store.guardarPlan(paquete, plan);
    void this.router.navigateByUrl('/registro/pago');
  }

  protected volver(): void {
    void this.router.navigateByUrl('/registro/datos');
  }
}
