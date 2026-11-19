import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule, ValidationErrors } from '@angular/forms';
import { startWith, switchMap } from 'rxjs';

export interface OpcionCampo {
  valor: string;
  etiqueta: string;
}

/** Mensaje de un error de validación: los validadores propios traen `{ mensaje }`. */
export function mensajeDeValidacion(errores: ValidationErrors | null): string | null {
  if (!errores) return null;
  if (errores['required']) return 'Este campo es obligatorio.';
  if (errores['email']) return 'Escribe un correo válido.';
  for (const valor of Object.values(errores)) {
    if (valor && typeof valor === 'object' && 'mensaje' in valor) {
      return String((valor as { mensaje: string }).mensaje);
    }
  }
  return 'El valor no es válido.';
}

/**
 * Campo de formulario: label con `for`, control (input o select), ayuda y error.
 * El error de validación sale cuando el campo fue tocado; el error del servidor (422) sale siempre.
 */
@Component({
  selector: 'app-campo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule],
  template: `
    <div class="campo" [class.con-error]="!!error()">
      <label [for]="nombre()">{{ etiqueta() }}</label>
      @if (tipo() === 'select') {
        <select
          [id]="nombre()"
          [formControl]="control()"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="descripcion()"
        >
          @if (opcionVacia()) {
            <option value="">{{ opcionVacia() }}</option>
          }
          @for (o of opciones(); track o.valor) {
            <option [value]="o.valor">{{ o.etiqueta }}</option>
          }
        </select>
      } @else if (tipo() === 'textarea') {
        <textarea
          class="area"
          [id]="nombre()"
          [formControl]="control()"
          [rows]="filas()"
          [attr.placeholder]="placeholder() || null"
          [attr.maxlength]="maxlength()"
          [attr.aria-invalid]="error() ? 'true' : null"
          [attr.aria-describedby]="descripcion()"
        ></textarea>
      } @else {
        <div class="envoltorio" [class.solo-lectura]="soloLectura()">
          <input
            [id]="nombre()"
            [type]="tipo()"
            [formControl]="control()"
            [readOnly]="soloLectura()"
            [attr.placeholder]="placeholder() || null"
            [attr.autocomplete]="autocompletar() || null"
            [attr.inputmode]="modoEntrada() || null"
            [attr.maxlength]="maxlength()"
            [attr.aria-invalid]="error() ? 'true' : null"
            [attr.aria-describedby]="descripcion()"
          />
          @if (verificado()) {
            <span class="verificado">✓ Verificado</span>
          }
        </div>
      }
      @if (error(); as e) {
        <p class="error" [id]="nombre() + '-error'" role="alert">{{ e }}</p>
      } @else if (ayuda()) {
        <p class="ayuda" [id]="nombre() + '-ayuda'">{{ ayuda() }}</p>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    .envoltorio {
      position: relative;
      display: flex;
    }
    .envoltorio input {
      flex: 1;
      min-width: 0;
    }
    .solo-lectura input {
      color: var(--tinta-2);
      background: var(--fondo);
      padding-right: 108px;
    }
    .verificado {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      padding: 2px 10px;
      font-size: 12px;
      font-weight: 600;
      color: var(--verde);
      background: var(--verde-claro);
      border-radius: 999px;
    }
    .campo textarea.area {
      height: auto;
      min-height: 96px;
      padding: 10px 12px;
      line-height: 1.45;
      resize: vertical;
    }
    .con-error input,
    .con-error select,
    .con-error textarea {
      border-color: var(--rojo);
    }
    .ayuda {
      font-size: 13px;
      color: var(--tinta-2);
    }
    p {
      margin: 0;
    }
  `,
})
export class Campo {
  readonly control = input.required<FormControl<string>>();
  /** Id del control (el `for` del label); no se llama `id` para no duplicar el atributo en el host. */
  readonly nombre = input.required<string>();
  readonly etiqueta = input.required<string>();
  readonly tipo = input<'text' | 'password' | 'email' | 'tel' | 'select' | 'textarea'>('text');
  readonly opciones = input<OpcionCampo[]>([]);
  readonly opcionVacia = input<string>('');
  readonly ayuda = input<string>('');
  readonly placeholder = input<string>('');
  readonly autocompletar = input<string>('');
  readonly modoEntrada = input<string>('');
  readonly maxlength = input<number | null>(null);
  readonly filas = input(4);
  readonly soloLectura = input(false);
  readonly verificado = input(false);
  /** Error devuelto por el servidor (422 con `campo`). */
  readonly errorServidor = input<string | null | undefined>(null);

  private readonly cambios = toSignal(
    toObservable(this.control).pipe(switchMap((c) => c.events.pipe(startWith(null)))),
  );

  protected readonly error = computed(() => {
    this.cambios();
    const servidor = this.errorServidor();
    if (servidor) return servidor;
    const c = this.control();
    return c.invalid && (c.touched || c.dirty) ? mensajeDeValidacion(c.errors) : null;
  });

  protected readonly descripcion = computed(() =>
    this.error() ? `${this.nombre()}-error` : this.ayuda() ? `${this.nombre()}-ayuda` : null,
  );
}
