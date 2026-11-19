import { ChangeDetectionStrategy, Component, input } from '@angular/core';

const PASOS = ['Tus datos', 'Paquete y plan', 'Dirección y pago'];

/** Encabezado de cada paso: "Crear cuenta · Paso n de 3", título, subtítulo y el avance. */
@Component({
  selector: 'app-cabecera-paso',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <p class="migas">Crear cuenta · Paso {{ paso() }} de 3</p>
    <h1>{{ titulo() }}</h1>
    <p class="subtitulo">{{ subtitulo() }}</p>
    <ol class="pasos" aria-label="Avance del registro">
      @for (nombre of pasos; track nombre; let i = $index) {
        <li
          [class.actual]="i + 1 === paso()"
          [class.hecho]="i + 1 < paso()"
          [attr.aria-current]="i + 1 === paso() ? 'step' : null"
        >
          <span class="bolita" aria-hidden="true">{{ i + 1 < paso() ? '✓' : i + 1 }}</span>
          <span class="nombre">{{ nombre }}</span>
          @if (i + 1 < paso()) {
            <span class="solo-lector">(completado)</span>
          }
        </li>
      }
    </ol>
  `,
  styles: `
    :host {
      display: block;
    }
    .migas {
      font-size: 14px;
      color: var(--tinta-2);
    }
    h1 {
      margin: 8px 0 12px;
      font-size: 32px;
    }
    .subtitulo {
      margin-bottom: 28px;
      font-size: 16px;
      color: var(--tinta-2);
    }
    .pasos {
      display: flex;
      align-items: center;
      gap: 16px;
      margin: 0 0 28px;
      padding: 0;
      list-style: none;
    }
    li {
      display: flex;
      flex: 1;
      align-items: center;
      gap: 12px;
      color: var(--tinta-2);
    }
    li:last-child {
      flex: 0 0 auto;
    }
    li:not(:last-child)::after {
      content: '';
      flex: 1;
      height: 2px;
      margin-left: 4px;
      background: var(--linea);
    }
    .bolita {
      display: grid;
      flex-shrink: 0;
      place-items: center;
      width: 32px;
      height: 32px;
      font-weight: 700;
      background: var(--blanco);
      border: 1.5px solid var(--linea);
      border-radius: 50%;
    }
    .actual {
      font-weight: 700;
      color: var(--tinta);
    }
    .actual .bolita {
      color: var(--verde);
      border-color: var(--verde);
    }
    .hecho .bolita {
      color: var(--blanco);
      background: var(--verde);
      border-color: var(--verde);
    }
    @media (max-width: 768px) {
      .nombre {
        display: none;
      }
      .actual .nombre {
        display: inline;
      }
    }
  `,
})
export class CabeceraPaso {
  readonly paso = input.required<1 | 2 | 3>();
  readonly titulo = input.required<string>();
  readonly subtitulo = input.required<string>();
  protected readonly pasos = PASOS;
}
