import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ContingenciaStore } from '../core/contingencia.store';

@Component({
  selector: 'app-banner-contingencia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (contingencia.activa()) {
      <div class="aviso contingencia banner" role="status">
        <p>{{ contingencia.texto() }}</p>
        <button type="button" class="boton secundario" (click)="contingencia.descartar()">
          Entendido
        </button>
      </div>
    }
  `,
  styles: `
    .banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      border-radius: 0;
      border-width: 0 0 1px;
      font-weight: 600;
    }
    .boton {
      height: 32px;
      flex-shrink: 0;
    }
  `,
})
export class BannerContingencia {
  protected readonly contingencia = inject(ContingenciaStore);
}
