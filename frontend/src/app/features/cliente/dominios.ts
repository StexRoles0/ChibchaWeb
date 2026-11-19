import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom, startWith } from 'rxjs';
import { EXTENSIONES_DOMINIO, DominiosApi, ExtensionDominio } from '../../core/api/dominios.api';
import { ResumenDTO } from '../../core/api/dto';
import { ErrorApi } from '../../core/errores';
import { Campo } from '../../shared/campo';
import { campoDelError, ErroresCampo } from '../../shared/errores-formulario';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { fechaDMA } from '../../shared/formato';
import { nombreDominio } from '../../shared/formularios/validadores';
import { noVacio } from '../../shared/formularios/validadores';
import { CeldaTabla, ColumnaTabla, Tabla } from '../../shared/tabla';

/** Texto de la etiqueta según el estado de la solicitud (RN-17). */
const ETIQUETAS: Record<string, string> = {
  REGISTRADA: 'Registrada',
  ENVIADA: 'Enviada al registrador',
  FALLIDA: 'Fallida',
};

/**
 * M-09 · Dominios (CU-DOM-01 y CU-DOM-02). Un solo `POST /dominios/solicitudes` registra la
 * solicitud (RN-16) y la envía al registrador (RN-17); la respuesta trae el estado final.
 */
@Component({
  selector: 'app-dominios',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Campo, Tabla, CeldaTabla, EtiquetaEstado],
  template: `
    <section class="pagina">
      <div>
        <p class="migas"><a routerLink="/cliente">Inicio</a> / Dominios</p>
        <h1>Solicitar un dominio</h1>
        <p class="subtitulo">Enviamos tu solicitud a un registrador de dominios externo.</p>
      </div>

      <div class="columnas">
        <form class="tarjeta" [formGroup]="form" (ngSubmit)="enviar()" novalidate>
          <h2>Nueva solicitud</h2>

          <div class="fila-dominio">
            <app-campo
              nombre="nombre"
              etiqueta="Nombre del dominio"
              [control]="form.controls.nombre"
              autocompletar="off"
              [maxlength]="80"
              [errorServidor]="errores.de('nombre')"
            />
            <app-campo
              nombre="extension"
              etiqueta="Extensión"
              tipo="select"
              [opciones]="extensiones"
              [control]="form.controls.extension"
              [errorServidor]="errores.de('extension')"
            />
          </div>
          <p class="ayuda" id="ayuda-formato">
            Letras, números y guiones; sin guion al inicio o al final; máximo 63 caracteres.
          </p>

          @if (formatoValido()) {
            <div class="aviso exito" role="status">
              <span aria-hidden="true">✓ </span>{{ dominioCompleto() }} tiene un formato válido.
            </div>
          }

          @if (resultado(); as r) {
            @if (r.estado === 'FALLIDA') {
              <div class="aviso advertencia" role="alert">
                <strong>{{ r.dominio }}</strong> quedó como fallida: el registrador no la aceptó.
                Puedes enviar una solicitud nueva.
              </div>
            } @else {
              <div class="aviso exito" role="status">
                Solicitud de <strong>{{ r.dominio }}</strong> enviada al registrador.
              </div>
            }
          }
          @if (errorGeneral(); as e) {
            <div class="aviso error" role="alert"><span aria-hidden="true">⚠ </span>{{ e }}</div>
          }

          <button type="submit" class="boton ancho" [disabled]="enviando()">
            {{ enviando() ? 'Enviando…' : 'Enviar solicitud' }}
          </button>
        </form>

        <div class="tarjeta sin-relleno">
          <h2 class="titulo-tabla">Solicitudes enviadas</h2>
          @if (errorLista(); as e) {
            <div class="aviso error margen" role="alert">
              <p>{{ e }}</p>
              <button type="button" class="boton secundario" (click)="cargar()">Reintentar</button>
            </div>
          } @else if (cargando() && filas().length === 0) {
            <p class="cargando" role="status">Cargando solicitudes…</p>
          } @else {
            <app-tabla
              [columnas]="columnas()"
              [filas]="filas()"
              descripcion="Solicitudes de dominio"
              textoVacio="Aún no has solicitado ningún dominio."
            >
              <ng-template appCelda let-fila let-columna="columna">
                @switch (columna.clave) {
                  @case ('estado') {
                    <app-etiqueta-estado
                      [estado]="fila.estado"
                      [etiqueta]="etiqueta(fila.estado)"
                    />
                  }
                  @case ('subtitulo') {
                    {{ fecha(fila.subtitulo) }}
                  }
                  @default {
                    {{ fila[columna.clave] }}
                  }
                }
              </ng-template>
            </app-tabla>
          }
        </div>
      </div>
    </section>
  `,
  styles: `
    .columnas {
      display: grid;
      grid-template-columns: minmax(0, 5fr) minmax(0, 7fr);
      gap: 28px;
      align-items: start;
    }
    form.tarjeta {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 28px 32px;
    }
    .fila-dominio {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 118px;
      gap: 16px;
      align-items: start;
    }
    .ayuda {
      margin-top: -8px;
      font-size: 13px;
      color: var(--tinta-2);
    }
    .ancho {
      width: 100%;
    }
    .titulo-tabla {
      padding: 20px 24px 16px;
    }
    .margen {
      margin: 0 24px 24px;
    }
    .cargando {
      padding: 24px;
      color: var(--tinta-2);
    }
    @media (max-width: 1100px) {
      .columnas {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class Dominios implements OnInit {
  private readonly api = inject(DominiosApi);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly extensiones = EXTENSIONES_DOMINIO.map((e) => ({ valor: e, etiqueta: e }));
  protected readonly form = new FormGroup({
    nombre: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, noVacio, nombreDominio],
    }),
    extension: new FormControl<string>('.com', { nonNullable: true }),
  });
  protected readonly errores = new ErroresCampo([this.form]);

  private readonly valores = toSignal(this.form.valueChanges.pipe(startWith(null)));
  protected readonly dominioCompleto = computed(() => {
    this.valores();
    const v = this.form.getRawValue();
    return `${v.nombre.trim().toLowerCase()}${v.extension}`;
  });
  protected readonly formatoValido = computed(() => {
    this.valores();
    return this.form.controls.nombre.value.trim() !== '' && this.form.controls.nombre.valid;
  });

  protected readonly filas = signal<ResumenDTO[]>([]);
  protected readonly cargando = signal(true);
  protected readonly errorLista = signal<string | null>(null);
  protected readonly enviando = signal(false);
  protected readonly errorGeneral = signal<string | null>(null);
  protected readonly resultado = signal<{ dominio: string; estado: string } | null>(null);

  /** La fecha (`subtitulo`) solo aparece si el servidor la trae. */
  protected readonly columnas = computed<ColumnaTabla[]>(() => [
    { clave: 'titulo', titulo: 'Dominio' },
    ...(this.filas().some((f) => f.subtitulo) ? [{ clave: 'subtitulo', titulo: 'Fecha' }] : []),
    { clave: 'estado', titulo: 'Estado' },
  ]);

  ngOnInit(): void {
    this.cargar();
    this.form.controls.nombre.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.resultado.set(null));
  }

  protected etiqueta(estado: string): string {
    return ETIQUETAS[estado.toUpperCase()] ?? estado;
  }

  protected fecha(valor: string): string {
    return fechaDMA(valor);
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.errorLista.set(null);
    try {
      this.filas.set(await firstValueFrom(this.api.solicitudes()));
    } catch (e) {
      this.errorLista.set((e as ErrorApi).mensaje);
    } finally {
      this.cargando.set(false);
    }
  }

  protected async enviar(): Promise<void> {
    this.errorGeneral.set(null);
    this.errores.limpiar();
    this.resultado.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    const dominio = this.dominioCompleto();
    try {
      const r = await firstValueFrom(
        this.api.solicitar({
          nombre: this.form.controls.nombre.value.trim().toLowerCase(),
          extension: this.form.controls.extension.value as ExtensionDominio,
        }),
      );
      if (r.estado !== 'FALLIDA') this.form.controls.nombre.reset('');
      this.resultado.set({ dominio, estado: r.estado });
      await this.cargar();
    } catch (e) {
      const err = e as ErrorApi;
      const campo = campoDelError(err);
      if (campo && campo in this.form.controls) this.errores.fijar(campo, err.mensaje);
      // 503 CONTINGENCIA: lo muestra el banner global.
      else if (err.codigo !== 'CONTINGENCIA') this.errorGeneral.set(err.mensaje);
    } finally {
      this.enviando.set(false);
    }
  }
}
