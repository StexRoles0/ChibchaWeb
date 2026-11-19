import { ChangeDetectionStrategy, Component } from '@angular/core';

/** Sol + "ChibchaWEB" (la parte WEB en oro). */
@Component({
  selector: 'app-marca',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg viewBox="0 0 32 32" aria-hidden="true" width="28" height="28">
      <circle cx="16" cy="16" r="6" fill="currentColor" />
      <g stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path
          d="M16 2v5M16 25v5M2 16h5M25 16h5M6 6l3.5 3.5M22.5 22.5L26 26M26 6l-3.5 3.5M9.5 22.5L6 26"
        />
      </g>
    </svg>
    <span>Chibcha<b>WEB</b></span>
  `,
  styles: `
    :host {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-size: 22px;
      font-weight: 700;
      color: var(--blanco);
    }
    svg,
    b {
      color: var(--oro);
    }
  `,
})
export class Marca {}
