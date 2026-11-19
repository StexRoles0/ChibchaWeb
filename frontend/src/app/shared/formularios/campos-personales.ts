import { ChangeDetectionStrategy, Component, effect, input } from '@angular/core';
import { FormControl } from '@angular/forms';
import { Campo } from '../campo';
import { FormPersonal, PLATAFORMAS } from './personal';

/** Campos de M-02 y de la pestaña PERSONAL de M-07. */
@Component({
  selector: 'app-campos-personales',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Campo],
  template: `
    <div class="rejilla">
      <app-campo
        nombre="nombre"
        etiqueta="Nombre completo"
        [control]="form().controls.nombre"
        autocompletar="name"
        [errorServidor]="errores()['nombre']"
      />
      <app-campo
        nombre="correo"
        etiqueta="Correo electrónico"
        tipo="email"
        [control]="correoControl"
        [soloLectura]="true"
        [verificado]="true"
        ayuda="El correo viene verificado del proveedor y no se puede editar."
      />
      <app-campo
        nombre="telefono"
        etiqueta="Teléfono"
        tipo="tel"
        [control]="form().controls.telefono"
        autocompletar="tel"
        [errorServidor]="errores()['telefono']"
      />
      <app-campo
        nombre="lineaResidencia"
        etiqueta="Dirección de residencia"
        [control]="form().controls.lineaResidencia"
        autocompletar="street-address"
        [errorServidor]="errores()['lineaResidencia']"
      />
      <app-campo
        nombre="ciudadResidencia"
        etiqueta="Ciudad de residencia"
        [control]="form().controls.ciudadResidencia"
        autocompletar="address-level2"
        [errorServidor]="errores()['ciudadResidencia']"
      />
      <app-campo
        nombre="codigoPostalResidencia"
        etiqueta="Código postal"
        [control]="form().controls.codigoPostalResidencia"
        autocompletar="postal-code"
        [errorServidor]="errores()['codigoPostalResidencia']"
      />
      <app-campo
        nombre="sitio"
        [etiqueta]="conDistribuidor() ? 'Sitio web a hospedar' : 'Sitio web'"
        [control]="form().controls.sitio"
        [ayuda]="
          'Tu subdominio será ' +
          (form().controls.sitio.value.trim().toLowerCase() || 'minegocio') +
          '.chibchaweb.com'
        "
        [errorServidor]="errores()['sitio']"
      />
      <app-campo
        nombre="plataforma"
        etiqueta="Plataforma"
        tipo="select"
        [opciones]="plataformas"
        [control]="form().controls.plataforma"
        [errorServidor]="errores()['plataforma']"
      />
      @if (conDistribuidor()) {
        <app-campo
          nombre="codigoDistribuidor"
          etiqueta="Código de distribuidor (opcional)"
          [control]="form().controls.codigoDistribuidor"
          placeholder="Si alguien te refirió, ingresa su código"
          ayuda="Si el código no corresponde a un distribuidor activo, te lo indicaremos para que lo corrijas."
          [errorServidor]="errores()['codigoDistribuidor']"
        />
      }
    </div>
  `,
  styles: `
    .rejilla {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 24px 28px;
    }
    @media (max-width: 768px) {
      .rejilla {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class CamposPersonales {
  readonly form = input.required<FormPersonal>();
  readonly correo = input.required<string>();
  readonly conDistribuidor = input(false);
  readonly errores = input<Record<string, string>>({});

  protected readonly plataformas = PLATAFORMAS;
  protected readonly correoControl = new FormControl('', { nonNullable: true });

  constructor() {
    effect(() => this.correoControl.setValue(this.correo()));
  }
}
