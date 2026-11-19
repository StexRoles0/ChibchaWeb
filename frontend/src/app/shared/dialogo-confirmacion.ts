import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  afterNextRender,
  input,
  OnDestroy,
  output,
  viewChild,
} from '@angular/core';

const ENFOCABLES =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Diálogo modal con foco atrapado: Tab y Shift+Tab rotan dentro, Escape cancela
 * y al cerrarse el foco vuelve al elemento que lo abrió.
 */
@Component({
  selector: 'app-dialogo-confirmacion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="fondo" (click)="cancelar.emit()" aria-hidden="true"></div>
    <div
      #caja
      class="dialogo"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialogo-titulo"
      (keydown)="teclado($event)"
    >
      <h2 id="dialogo-titulo">{{ titulo() }}</h2>
      <ng-content />
      <div class="acciones">
        <button type="button" class="boton secundario" (click)="cancelar.emit()">
          {{ textoCancelar() }}
        </button>
        <button
          type="button"
          class="boton"
          [class.peligro]="peligro()"
          [disabled]="deshabilitado() || ocupado()"
          (click)="confirmar.emit()"
        >
          {{ ocupado() ? 'Procesando…' : textoConfirmar() }}
        </button>
      </div>
    </div>
  `,
  styles: `
    :host {
      position: fixed;
      inset: 0;
      z-index: 50;
      display: grid;
      place-items: center;
      padding: 16px;
    }
    .fondo {
      position: absolute;
      inset: 0;
      background: rgb(24 35 31 / 55%);
    }
    .dialogo {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 16px;
      width: min(500px, 100%);
      max-height: 100%;
      overflow: auto;
      padding: 28px;
      background: var(--blanco);
      border-radius: 16px;
      box-shadow: 0 20px 50px rgb(0 0 0 / 30%);
    }
    .acciones {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
    .peligro {
      background: var(--rojo);
      border-color: var(--rojo);
    }
    .peligro:hover:not(:disabled) {
      background: #8f1c12;
    }
  `,
})
export class DialogoConfirmacion implements OnDestroy {
  readonly titulo = input.required<string>();
  readonly textoConfirmar = input('Confirmar');
  readonly textoCancelar = input('Cancelar');
  readonly peligro = input(false);
  readonly deshabilitado = input(false);
  readonly ocupado = input(false);
  readonly confirmar = output<void>();
  readonly cancelar = output<void>();

  private readonly caja = viewChild.required<ElementRef<HTMLElement>>('caja');
  private readonly previo = document.activeElement as HTMLElement | null;

  constructor() {
    afterNextRender(() => {
      const caja = this.caja().nativeElement;
      const inicial =
        caja.querySelector<HTMLElement>('[data-foco-inicial]') ??
        caja.querySelector<HTMLElement>(ENFOCABLES);
      inicial?.focus();
    });
  }

  ngOnDestroy(): void {
    this.previo?.focus?.();
  }

  protected teclado(ev: KeyboardEvent): void {
    if (ev.key === 'Escape') {
      ev.stopPropagation();
      this.cancelar.emit();
      return;
    }
    if (ev.key !== 'Tab') return;
    const foco = Array.from(this.caja().nativeElement.querySelectorAll<HTMLElement>(ENFOCABLES));
    if (foco.length === 0) return;
    const primero = foco[0];
    const ultimo = foco[foco.length - 1];
    const activo = document.activeElement;
    if (ev.shiftKey && activo === primero) {
      ev.preventDefault();
      ultimo.focus();
    } else if (!ev.shiftKey && activo === ultimo) {
      ev.preventDefault();
      primero.focus();
    }
  }
}
