import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { Campo } from '../campo';
import { FormPago, FRANQUICIAS } from './pago';

/** Campos de M-04 y de la pestaña PAGO de M-07. */
@Component({
  selector: 'app-campos-pago',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Campo],
  template: `
    <div class="rejilla">
      <app-campo
        nombre="lineaFacturacion"
        etiqueta="Dirección de facturación"
        [control]="form().controls.lineaFacturacion"
        autocompletar="billing street-address"
        [errorServidor]="errores()['lineaFacturacion']"
      />
      <app-campo
        nombre="ciudadFacturacion"
        etiqueta="Ciudad"
        [control]="form().controls.ciudadFacturacion"
        autocompletar="billing address-level2"
        [errorServidor]="errores()['ciudadFacturacion']"
      />
      <app-campo
        nombre="codigoPostalFacturacion"
        etiqueta="Código postal"
        [control]="form().controls.codigoPostalFacturacion"
        autocompletar="billing postal-code"
        [errorServidor]="errores()['codigoPostalFacturacion']"
      />
      <app-campo
        nombre="franquicia"
        etiqueta="Franquicia"
        tipo="select"
        [opciones]="franquicias"
        [control]="form().controls.franquicia"
        [errorServidor]="errores()['franquicia']"
      />
      <app-campo
        nombre="numeroTarjeta"
        etiqueta="Número de tarjeta"
        [control]="form().controls.numeroTarjeta"
        autocompletar="cc-number"
        modoEntrada="numeric"
        [maxlength]="23"
        [errorServidor]="errores()['numeroTarjeta']"
      />
      <div class="fila-tarjeta">
        <app-campo
          nombre="vencimiento"
          etiqueta="Vencimiento"
          [control]="form().controls.vencimiento"
          autocompletar="cc-exp"
          modoEntrada="numeric"
          placeholder="MM/AA"
          [maxlength]="5"
          [errorServidor]="errores()['vencimiento']"
        />
        <app-campo
          nombre="codigoSeguridad"
          etiqueta="Código de seguridad"
          tipo="password"
          [control]="form().controls.codigoSeguridad"
          autocompletar="cc-csc"
          modoEntrada="numeric"
          [maxlength]="4"
          ayuda="No se almacena."
          [errorServidor]="errores()['codigoSeguridad']"
        />
      </div>
    </div>
  `,
  styles: `
    .rejilla {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 24px 28px;
    }
    .fila-tarjeta {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }
    @media (max-width: 768px) {
      .rejilla {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class CamposPago {
  readonly form = input.required<FormPago>();
  readonly errores = input<Record<string, string>>({});
  protected readonly franquicias = FRANQUICIAS;
}
