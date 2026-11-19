import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { Algoritmo, ALGORITMOS, ContingenciaApi } from '../../core/api/contingencia.api';
import { ResumenDTO } from '../../core/api/dto';
import { ErrorApi } from '../../core/errores';
import { etiquetaEvento } from '../../shared/evento-respaldo';
import { CeldaTabla, ColumnaTabla, Tabla } from '../../shared/tabla';

/**
 * M-20 · Contingencia de base de datos (RT04). Algoritmo de cifrado del respaldo (RN-29),
 * eventos pendientes en el archivo de respaldo y sincronización (RN-30).
 */
@Component({
  selector: 'app-contingencia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Tabla, CeldaTabla],
  template: `
    <section class="pagina">
      <div>
        <p class="migas"><a routerLink="/admin">Administración</a> / Contingencia</p>
        <h1>Contingencia de base de datos</h1>
        <p class="subtitulo">
          Si la base de datos falla tras una acción irreversible, el evento se respalda cifrado en
          un archivo plano.
        </p>
      </div>

      <div class="columnas">
        <form class="tarjeta" (submit)="aplicar($event)">
          <h2>Algoritmo de cifrado</h2>
          <p class="texto">
            Se aplica a los respaldos nuevos. Cada registro guarda con qué algoritmo se cifró.
          </p>

          <fieldset class="segmentos">
            <legend class="solo-lector">Algoritmo de cifrado</legend>
            @for (a of algoritmos; track a) {
              <label class="segmento" [class.activo]="algoritmo.value === a">
                <input
                  type="radio"
                  name="algoritmo"
                  [value]="a"
                  [attr.value]="a"
                  [formControl]="algoritmo"
                />
                <span>{{ a }}</span>
              </label>
            }
          </fieldset>

          @if (avisoAlgoritmo(); as a) {
            <div class="aviso exito" role="status">{{ a }}</div>
          }
          @if (errorAlgoritmo(); as e) {
            <div class="aviso error" role="alert"><span aria-hidden="true">⚠ </span>{{ e }}</div>
          }

          <div class="pie pie-algoritmo">
            <p class="ayuda">
              El servidor no informa el algoritmo vigente; aquí se parte de AES hasta que lo
              cambies.
            </p>
            <button type="submit" class="boton" [disabled]="aplicando()">
              {{ aplicando() ? 'Aplicando…' : 'Aplicar algoritmo' }}
            </button>
          </div>
        </form>

        <div class="tarjeta">
          <h2>Respaldo pendiente</h2>
          <p class="texto" role="status">
            @if (cargando()) {
              Consultando el respaldo…
            } @else if (!errorLista()) {
              {{ pendientes().length }}
              {{ pendientes().length === 1 ? 'evento pendiente' : 'eventos pendientes' }} de
              sincronizar.
            }
          </p>

          @if (errorLista(); as e) {
            <div class="aviso error" role="alert">
              <p>{{ e }}</p>
              <button type="button" class="boton secundario" (click)="cargar()">Reintentar</button>
            </div>
          } @else if (!cargando()) {
            <div class="tabla">
              <app-tabla
                [columnas]="columnas"
                [filas]="pendientes()"
                descripcion="Eventos pendientes en el respaldo"
                textoVacio="No hay eventos pendientes en el respaldo."
              >
                <ng-template appCelda let-fila let-columna="columna">
                  @if (columna.clave === 'titulo') {
                    {{ evento(fila.titulo) }}
                  } @else {
                    {{ fila[columna.clave] }}
                  }
                </ng-template>
              </app-tabla>
            </div>
          }

          @if (resultadoSync(); as r) {
            <div
              class="aviso"
              [class]="r.clase"
              [attr.role]="r.clase === 'error' ? 'alert' : 'status'"
            >
              {{ r.texto }}
            </div>
          }

          <div class="pie">
            <button
              type="button"
              class="boton"
              [disabled]="sincronizando() || pendientes().length === 0"
              (click)="sincronizar()"
            >
              {{
                sincronizando()
                  ? 'Sincronizando…'
                  : 'Sincronizar respaldo (' + pendientes().length + ')'
              }}
            </button>
          </div>
        </div>
      </div>
    </section>
  `,
  styles: `
    .columnas {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 28px;
      align-items: start;
    }
    .tarjeta {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 28px 32px;
    }
    .texto,
    .ayuda {
      color: var(--tinta-2);
    }
    .ayuda {
      font-size: 13px;
    }
    fieldset {
      min-width: 0;
      margin: 0;
      padding: 0;
      border: 0;
    }
    .segmentos {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      overflow: hidden;
      border: 1px solid var(--linea);
      border-radius: 10px;
    }
    .segmento {
      position: relative;
      display: grid;
      place-items: center;
      height: 46px;
      font-weight: 500;
      cursor: pointer;
      border-left: 1px solid var(--linea);
    }
    .segmento:first-of-type {
      border-left: 0;
    }
    .segmento input {
      position: absolute;
      opacity: 0;
      inset: 0;
      cursor: pointer;
    }
    .segmento.activo {
      font-weight: 700;
      color: var(--blanco);
      background: var(--verde);
    }
    .segmento:has(input:focus-visible) {
      outline: 2px solid var(--verde-2);
      outline-offset: -3px;
    }
    .pie {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .pie .boton {
      margin-left: auto;
      white-space: nowrap;
    }
    .pie-algoritmo {
      flex-direction: column;
      align-items: stretch;
    }
    @media (max-width: 1100px) {
      .columnas {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class Contingencia implements OnInit {
  private readonly api = inject(ContingenciaApi);

  protected readonly algoritmos = ALGORITMOS;
  protected readonly algoritmo = new FormControl<Algoritmo>('AES', { nonNullable: true });
  protected readonly columnas: ColumnaTabla[] = [
    { clave: 'titulo', titulo: 'Tipo de evento' },
    { clave: 'subtitulo', titulo: 'Algoritmo' },
  ];

  protected readonly pendientes = signal<ResumenDTO[]>([]);
  protected readonly cargando = signal(true);
  protected readonly errorLista = signal<string | null>(null);

  protected readonly aplicando = signal(false);
  protected readonly avisoAlgoritmo = signal<string | null>(null);
  protected readonly errorAlgoritmo = signal<string | null>(null);

  protected readonly sincronizando = signal(false);
  protected readonly resultadoSync = signal<{ clase: string; texto: string } | null>(null);

  protected evento(tipo: string): string {
    return etiquetaEvento(tipo);
  }

  ngOnInit(): void {
    void this.cargar();
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.errorLista.set(null);
    try {
      this.pendientes.set(await firstValueFrom(this.api.pendientes()));
    } catch (e) {
      this.errorLista.set((e as ErrorApi).mensaje);
    } finally {
      this.cargando.set(false);
    }
  }

  protected async aplicar(ev?: Event): Promise<void> {
    ev?.preventDefault();
    this.avisoAlgoritmo.set(null);
    this.errorAlgoritmo.set(null);
    this.aplicando.set(true);
    const nombre = this.algoritmo.value;
    try {
      await firstValueFrom(this.api.cambiarAlgoritmo(nombre));
      this.avisoAlgoritmo.set(
        `Algoritmo aplicado: ${nombre}. Los respaldos nuevos usarán este cifrado.`,
      );
    } catch (e) {
      const err = e as ErrorApi;
      if (err.codigo !== 'CONTINGENCIA') this.errorAlgoritmo.set(err.mensaje);
    } finally {
      this.aplicando.set(false);
    }
  }

  protected async sincronizar(): Promise<void> {
    this.resultadoSync.set(null);
    this.sincronizando.set(true);
    const antes = this.pendientes().length;
    try {
      const r = await firstValueFrom(this.api.sincronizar());
      await this.cargar();
      const quedan = this.pendientes().length;
      this.resultadoSync.set(
        quedan > 0 && r.sincronizados < antes
          ? {
              clase: 'advertencia',
              texto: `La sincronización se detuvo tras ${r.sincronizados} de ${antes} eventos; el respaldo no se vació.`,
            }
          : {
              clase: 'exito',
              texto: `Se sincronizaron ${r.sincronizados} ${r.sincronizados === 1 ? 'evento' : 'eventos'}. El respaldo quedó al día.`,
            },
      );
    } catch (e) {
      const err = e as ErrorApi;
      this.resultadoSync.set(
        err.codigo === 'CONTINGENCIA'
          ? {
              clase: 'advertencia',
              texto: 'La base de datos sigue sin responder; el respaldo se conserva intacto.',
            }
          : {
              clase: 'error',
              // Todo o nada (D-27): si un evento falla, no se aplica ninguno y el respaldo se conserva.
              texto:
                err.estado === 422
                  ? `${err.mensaje} No se aplicó ningún evento; el respaldo se conserva.`
                  : err.mensaje,
            },
      );
    } finally {
      this.sincronizando.set(false);
    }
  }
}
