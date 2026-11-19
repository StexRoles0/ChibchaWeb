import { ChangeDetectionStrategy, Component, computed, input, model } from '@angular/core';
import { aMontoTexto } from './resumen-monto';
import { Paquete, Plan, porcentaje } from './catalogo';
import { MontoPipe } from './monto';

let contador = 0;

/** Tarjetas de paquete, plan de pago y vista previa del monto del periodo (RN-01). */
@Component({
  selector: 'app-selector-paquete-plan',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MontoPipe],
  template: `
    <fieldset class="paquetes">
      <legend class="solo-lector">Paquete</legend>
      @for (p of paquetes(); track p.id) {
        <label class="opcion paquete" [class.elegido]="p.id === idPaquete()">
          <input
            type="radio"
            [name]="nombre + '-paquete'"
            [value]="p.id"
            [checked]="p.id === idPaquete()"
            (change)="idPaquete.set(p.id)"
          />
          <span class="nombre">{{ p.nombre }}</span>
          <span class="precio"
            ><strong>{{ precioEntero(p) }}</strong
            ><small> /mes</small></span
          >
        </label>
      }
    </fieldset>

    <div class="inferior">
      <fieldset class="planes">
        <legend>Plan de pago</legend>
        <div class="segmentos">
          @for (pl of planes(); track pl.id) {
            <label class="opcion plan" [class.elegido]="pl.id === idPlan()">
              <input
                type="radio"
                [name]="nombre + '-plan'"
                [value]="pl.id"
                [checked]="pl.id === idPlan()"
                (change)="idPlan.set(pl.id)"
              />
              <span class="nombre">{{ pl.nombre }}</span>
              <small>{{
                pl.descuentoPuntosBasicos
                  ? '−' + pct(pl.descuentoPuntosBasicos) + ' %'
                  : 'sin descuento'
              }}</small>
            </label>
          }
        </div>
      </fieldset>

      <section class="resumen" aria-live="polite" aria-label="Resumen del monto">
        @if (desglose(); as d) {
          <p class="linea">
            <span>{{ d.paquete }} × {{ d.meses }} {{ d.meses === 1 ? 'mes' : 'meses' }}</span>
            <span>{{ d.bruto | monto }}</span>
          </p>
          <p class="linea">
            <span>{{
              d.descuentoPct === '0'
                ? 'Sin descuento'
                : 'Descuento ' + d.plan + ' (' + d.descuentoPct + ' %)'
            }}</span>
            <span>{{
              d.descuentoPct === '0' ? ('0.00' | monto) : '− ' + (d.descuento | monto)
            }}</span>
          </p>
          <p class="linea total">
            <span>Total por periodo</span>
            <span>{{ d.total | monto }}</span>
          </p>
        } @else {
          <p class="vacio">Elige un paquete y un plan para ver el total por periodo.</p>
        }
      </section>
    </div>
  `,
  styles: `
    fieldset {
      min-width: 0;
      margin: 0;
      padding: 0;
      border: 0;
    }
    legend {
      padding: 0;
      margin-bottom: 10px;
      font-weight: 700;
    }
    .paquetes {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 20px;
    }
    .opcion {
      position: relative;
      cursor: pointer;
      background: var(--blanco);
      border: 1px solid var(--linea);
    }
    .opcion input {
      position: absolute;
      opacity: 0;
      inset: 0;
      cursor: pointer;
    }
    .opcion:has(input:focus-visible) {
      outline: 2px solid var(--verde-2);
      outline-offset: 2px;
    }
    .paquete {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 20px 24px;
      border-radius: var(--radio);
    }
    .paquete.elegido {
      border: 2px solid var(--verde-2);
      padding: 19px 23px;
      background: #f7fbf9;
    }
    .paquete .nombre {
      font-weight: 700;
    }
    .precio strong {
      font-size: 32px;
    }
    .precio small {
      color: var(--tinta-2);
    }
    .inferior {
      display: grid;
      grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
      gap: 40px;
      margin-top: 24px;
      align-items: start;
    }
    .segmentos {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      border: 1px solid var(--linea);
      border-radius: 8px;
      overflow: hidden;
    }
    .plan {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 14px 8px;
      border: 0;
      border-right: 1px solid var(--linea);
      border-radius: 0;
    }
    .plan:last-child {
      border-right: 0;
    }
    .plan small {
      color: var(--tinta-2);
    }
    .plan.elegido {
      color: var(--blanco);
      background: var(--verde);
    }
    .plan.elegido small {
      color: var(--blanco);
    }
    .resumen {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-top: 26px;
      color: var(--tinta-2);
    }
    .linea {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin: 0;
    }
    .total {
      padding-top: 10px;
      font-size: 16px;
      font-weight: 700;
      color: var(--tinta);
      border-top: 1px solid var(--linea);
    }
    .vacio {
      margin: 0;
    }
    @media (max-width: 768px) {
      .paquetes,
      .inferior {
        grid-template-columns: minmax(0, 1fr);
      }
      .segmentos {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
  `,
})
export class SelectorPaquetePlan {
  readonly paquetes = input.required<Paquete[]>();
  readonly planes = input.required<Plan[]>();
  readonly idPaquete = model<number | null>(null);
  readonly idPlan = model<number | null>(null);

  protected readonly nombre = `sel${++contador}`;
  protected readonly pct = porcentaje;

  protected precioEntero(p: Paquete): string {
    return `US$ ${p.tarifaCentavos % 100 === 0 ? p.tarifaCentavos / 100 : p.tarifa}`;
  }

  protected readonly desglose = computed(() => {
    const paquete = this.paquetes().find((p) => p.id === this.idPaquete());
    const plan = this.planes().find((p) => p.id === this.idPlan());
    return paquete && plan ? aMontoTexto(paquete, plan) : null;
  });
}
