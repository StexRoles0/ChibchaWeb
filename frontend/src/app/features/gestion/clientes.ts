import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  OnInit,
  signal,
  viewChild,
  ElementRef,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  catchError,
  debounceTime,
  distinctUntilChanged,
  firstValueFrom,
  of,
  startWith,
  Subject,
  switchMap,
  tap,
} from 'rxjs';
import { ConsultasApi } from '../../core/api/consultas.api';
import { ResumenDTO } from '../../core/api/dto';
import { ErrorApi } from '../../core/errores';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { camposDeDetalle, fechaCorta, vencimientoCorto } from '../../shared/formato';
import { MontoPipe } from '../../shared/monto';
import { CeldaTabla, ColumnaTabla, Tabla } from '../../shared/tabla';
import { esActivo } from './personal';

const PLATAFORMAS: Record<string, string> = { UNIX: 'Unix', WINDOWS: 'Windows' };

/**
 * M-16 · Clientes (CU-CON-01 y CU-CON-02): solo consulta. *Ver detalle* abre un panel
 * lateral con `GET /consultas/CLIENTE/{id}`.
 */
@Component({
  selector: 'app-clientes-gestion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ReactiveFormsModule, Tabla, CeldaTabla, EtiquetaEstado, MontoPipe],
  template: `
    <section class="pagina">
      <div>
        <p class="migas"><a routerLink="/gestion">Inicio</a> / Clientes</p>
        <h1>Clientes</h1>
      </div>

      <div class="distribucion">
        <div class="tarjeta sin-relleno">
          <div class="barra-herramientas">
            <div class="campo buscador">
              <label for="buscar" class="solo-lector">Buscar clientes</label>
              <input
                id="buscar"
                type="search"
                autocomplete="off"
                placeholder="Buscar por nombre, correo o documento"
                [formControl]="buscar"
              />
            </div>
            <p class="conteo" role="status" aria-live="polite">
              @if (!error() && !cargando()) {
                Mostrando {{ filas().length }} {{ filas().length === 1 ? 'registro' : 'registros' }}
              }
            </p>
          </div>

          @if (error(); as e) {
            <div class="aviso error margen" role="alert">
              <p>{{ e }}</p>
              <button type="button" class="boton secundario" (click)="recargar()">
                Reintentar
              </button>
            </div>
          } @else if (cargando() && filas().length === 0) {
            <p class="cargando" role="status">Cargando clientes…</p>
          } @else {
            <app-tabla
              [columnas]="columnas"
              [filas]="filas()"
              descripcion="Listado de clientes"
              [textoVacio]="
                buscar.value.trim()
                  ? 'Ningún cliente coincide con la búsqueda.'
                  : 'Aún no hay clientes registrados.'
              "
            >
              <ng-template appCelda let-fila let-columna="columna">
                @switch (columna.clave) {
                  @case ('estado') {
                    <app-etiqueta-estado [estado]="fila.estado" />
                  }
                  @case ('acciones') {
                    <button
                      type="button"
                      class="enlace-accion sin-salto"
                      [attr.aria-pressed]="seleccionado()?.id === fila.id"
                      (click)="ver(fila)"
                    >
                      Ver detalle<span class="solo-lector"> de {{ fila.titulo }}</span>
                    </button>
                  }
                  @default {
                    {{ fila[columna.clave] }}
                  }
                }
              </ng-template>
            </app-tabla>
          }
        </div>

        @if (seleccionado(); as s) {
          <aside #panel class="tarjeta panel" aria-labelledby="panel-titulo" tabindex="-1">
            <div class="panel-cabecera">
              <h2 id="panel-titulo">{{ s.titulo }}</h2>
              <button type="button" class="enlace-accion" (click)="cerrar()">
                Cerrar<span class="solo-lector"> el detalle</span>
              </button>
            </div>

            @if (noEncontrado()) {
              <p class="aviso error" role="alert">Ese cliente ya no existe en el sistema.</p>
            } @else if (errorDetalle(); as e) {
              <div class="aviso error" role="alert">
                <p>{{ e }}</p>
                <button type="button" class="boton secundario reintento" (click)="ver(s)">
                  Reintentar
                </button>
              </div>
            } @else if (detalle(); as d) {
              <p class="estado">
                <app-etiqueta-estado [estado]="d['activo'] === 'true' ? 'ACTIVO' : 'INACTIVO'" />
              </p>
              <div class="secciones">
                <div>
                  <h3>Datos personales</h3>
                  <dl class="lista-datos">
                    <dt>Correo</dt>
                    <dd>{{ d['correo'] }}</dd>
                    <dt>Teléfono</dt>
                    <dd>{{ d['telefono'] }}</dd>
                    <dt>Residencia</dt>
                    <dd>{{ d['lineaResidencia'] }}, {{ d['ciudadResidencia'] }}</dd>
                    <dt>Distribuidor</dt>
                    <dd>{{ d['distribuidor'] || 'Sin distribuidor' }}</dd>
                  </dl>
                </div>
                <div>
                  <h3>Hospedaje</h3>
                  <dl class="lista-datos">
                    <dt>Sitio</dt>
                    <dd>{{ d['sitio'] }}</dd>
                    <dt>Plataforma</dt>
                    <dd>{{ plataforma(d['plataforma']) }}</dd>
                    <dt>Paquete</dt>
                    <dd>{{ d['paquete'] }}</dd>
                    <dt>Plan</dt>
                    <dd>{{ d['plan'] }} · {{ d['montoPeriodo'] | monto }}</dd>
                    <dt>Próximo corte</dt>
                    <dd>{{ fecha(d['fechaCorte']) }}</dd>
                  </dl>
                </div>
                <div>
                  <h3>Facturación</h3>
                  <dl class="lista-datos">
                    <dt>Medio de pago</dt>
                    <dd>{{ d['tarjeta'] }} · vence {{ vencimiento(d['vencimiento']) }}</dd>
                    <dt>Dirección</dt>
                    <dd>{{ d['lineaFacturacion'] }}, {{ d['ciudadFacturacion'] }}</dd>
                  </dl>
                </div>
              </div>
            } @else {
              <p role="status">Cargando detalle…</p>
            }
          </aside>
        }
      </div>
    </section>
  `,
  styles: `
    .distribucion {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 28px;
      align-items: start;
    }
    .sin-salto {
      white-space: nowrap;
    }
    .panel:focus {
      outline: none;
    }
    .margen {
      margin: 0 24px 24px;
    }
    .cargando {
      padding: 24px;
      color: var(--tinta-2);
    }
    .panel {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .panel-cabecera {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }
    .panel h3 {
      margin-top: 8px;
      font-size: 15px;
      color: var(--tinta-2);
    }
    .estado {
      margin: 0;
    }
    .reintento {
      margin-top: 8px;
    }
    .secciones {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px 32px;
    }
    @media (max-width: 1100px) {
      .secciones {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class ClientesGestion implements OnInit {
  private readonly api = inject(ConsultasApi);
  private readonly destroyRef = inject(DestroyRef);
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');

  protected readonly buscar = new FormControl('', { nonNullable: true });
  private readonly refresco = new Subject<void>();

  protected readonly filas = signal<ResumenDTO[]>([]);
  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly seleccionado = signal<ResumenDTO | null>(null);
  protected readonly detalle = signal<Record<string, string> | null>(null);
  protected readonly errorDetalle = signal<string | null>(null);
  protected readonly noEncontrado = signal(false);

  protected readonly columnas: ColumnaTabla[] = [
    { clave: 'titulo', titulo: 'Nombre' },
    { clave: 'subtitulo', titulo: 'Detalle' },
    { clave: 'estado', titulo: 'Estado' },
    { clave: 'acciones', titulo: 'Acciones', ocultarTitulo: true },
  ];

  protected readonly plataforma = (v: string) => PLATAFORMAS[v] ?? v;
  protected readonly fecha = fechaCorta;
  protected readonly vencimiento = vencimientoCorto;
  protected readonly esActivo = esActivo;

  ngOnInit(): void {
    const filtro$ = this.buscar.valueChanges.pipe(debounceTime(300), distinctUntilChanged());
    this.refresco
      .pipe(
        startWith(undefined),
        switchMap(() => filtro$.pipe(startWith(this.buscar.value))),
        tap(() => {
          this.cargando.set(true);
          this.error.set(null);
        }),
        switchMap((f) =>
          this.api.basico('CLIENTE', f.trim()).pipe(
            catchError((e: ErrorApi) => {
              this.error.set(e.mensaje ?? 'No se pudo cargar el listado.');
              return of<ResumenDTO[]>([]);
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((lista) => {
        this.filas.set(lista);
        this.cargando.set(false);
      });
  }

  protected recargar(): void {
    this.refresco.next();
  }

  /** `GET /consultas/CLIENTE/{id}` */
  protected async ver(fila: ResumenDTO): Promise<void> {
    this.seleccionado.set(fila);
    this.detalle.set(null);
    this.errorDetalle.set(null);
    this.noEncontrado.set(false);
    // El panel aparece debajo del listado: se enfoca para que se lea y quede a la vista.
    setTimeout(() => this.panel()?.nativeElement.focus());
    try {
      const d = await firstValueFrom(this.api.detalle('CLIENTE', fila.id));
      if (this.seleccionado()?.id === fila.id) this.detalle.set(camposDeDetalle(d));
    } catch (e) {
      const err = e as ErrorApi;
      if (err.estado === 404) this.noEncontrado.set(true);
      else this.errorDetalle.set(err.mensaje);
    }
  }

  protected cerrar(): void {
    this.seleccionado.set(null);
    this.detalle.set(null);
  }
}
