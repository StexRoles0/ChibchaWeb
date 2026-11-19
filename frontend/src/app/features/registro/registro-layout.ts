import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Marca } from '../../shared/marca';
import { RegistroStore } from './registro.store';

/** Marco del asistente de registro: barra con la marca y *Cancelar registro*. */
@Component({
  selector: 'app-registro-layout',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, Marca],
  template: `
    <header class="barra">
      <app-marca />
      <button type="button" class="cancelar" (click)="cancelar()">Cancelar registro</button>
    </header>
    <main class="contenedor">
      <router-outlet />
    </main>
  `,
  styles: `
    .barra {
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: var(--alto-barra);
      padding: 0 24px;
      background: var(--verde);
    }
    .cancelar {
      height: 36px;
      padding: 0 16px;
      font: inherit;
      color: var(--blanco);
      cursor: pointer;
      background: transparent;
      border: 1px solid rgb(255 255 255 / 55%);
      border-radius: 8px;
    }
    .cancelar:hover {
      background: rgb(255 255 255 / 12%);
    }
    .cancelar:focus-visible {
      outline-color: var(--blanco);
    }
    .contenedor {
      width: min(1040px, 100%);
      margin: 0 auto;
      padding: 40px 24px 56px;
    }
  `,
})
export class RegistroLayout {
  private readonly store = inject(RegistroStore);

  protected cancelar(): void {
    void this.store.cancelar();
  }
}
