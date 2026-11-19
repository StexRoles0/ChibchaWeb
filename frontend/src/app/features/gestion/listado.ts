import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
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
import { ResumenDTO } from '../../core/api/dto';
import { ErrorApi } from '../../core/errores';
import { DialogoConfirmacion } from '../../shared/dialogo-confirmacion';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { CeldaTabla, ColumnaTabla, Tabla } from '../../shared/tabla';
import { apiDeTipo, configDeRuta, esActivo } from './personal';

/**
 * M-12 · Empleados (CU-EMP-01, CU-EMP-04, CU-CON-01) y M-15 · Distribuidores (CU-DIS-01, CU-DIS-04).
 * La baja es lógica y pide confirmación en un diálogo modal.
 */
@Component({
  selector: 'app-listado-personal',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    Tabla,
    CeldaTabla,
    EtiquetaEstado,
    DialogoConfirmacion,
  ],
  template: `
    <section class="pagina">
      <div class="encabezado-pagina">
        <div>
          <p class="migas"><a routerLink="/gestion">Inicio</a> / {{ config.plural }}</p>
          <h1>{{ config.plural }}</h1>
        </div>
        <a class="boton" [routerLink]="config.ruta + '/nuevo'">+ Crear {{ config.singular }}</a>
      </div>

      @if (aviso(); as a) {
        <div class="aviso exito" role="status">{{ a }}</div>
      }

      <div class="tarjeta sin-relleno">
        <div class="barra-herramientas">
          <div class="campo buscador">
            <label for="buscar" class="solo-lector">Buscar {{ config.plural.toLowerCase() }}</label>
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
            <button type="button" class="boton secundario" (click)="recargar()">Reintentar</button>
          </div>
        } @else if (cargando() && filas().length === 0) {
          <p class="cargando" role="status">Cargando {{ config.plural.toLowerCase() }}…</p>
        } @else {
          <app-tabla
            [columnas]="columnas"
            [filas]="filas()"
            [descripcion]="'Listado de ' + config.plural.toLowerCase()"
            [textoVacio]="textoVacio()"
          >
            <ng-template appCelda let-fila let-columna="columna">
              @switch (columna.clave) {
                @case ('estado') {
                  <app-etiqueta-estado [estado]="fila.estado" />
                }
                @case ('acciones') {
                  <div class="acciones-fila">
                    <a class="enlace-accion" [routerLink]="config.ruta + '/' + fila.id"
                      >Ver<span class="solo-lector"> {{ fila.titulo }}</span></a
                    >
                    <span class="separador" aria-hidden="true">·</span>
                    <a class="enlace-accion" [routerLink]="config.ruta + '/' + fila.id + '/editar'"
                      >Editar<span class="solo-lector"> {{ fila.titulo }}</span></a
                    >
                    <span class="separador" aria-hidden="true">·</span>
                    <button
                      type="button"
                      class="enlace-accion peligro"
                      [disabled]="!activo(fila)"
                      (click)="pedirBaja(fila)"
                    >
                      Eliminar<span class="solo-lector"> {{ fila.titulo }}</span>
                    </button>
                  </div>
                }
                @default {
                  {{ fila[columna.clave] }}
                }
              }
            </ng-template>
          </app-tabla>
        }
      </div>
    </section>

    @if (porEliminar(); as r) {
      <app-dialogo-confirmacion
        [titulo]="'Dar de baja ' + config.articulo + ' ' + config.singular"
        textoConfirmar="Dar de baja"
        [peligro]="true"
        [ocupado]="eliminando()"
        (confirmar)="confirmarBaja()"
        (cancelar)="cancelarBaja()"
      >
        <p>
          ¿Quieres dar de baja a <strong>{{ r.titulo }}</strong
          >?
          @if (config.tipo === 'empleado') {
            Quedará inactivo y no podrá iniciar sesión.
          } @else {
            Quedará inactivo y su código ya no servirá en nuevos registros.
          }
          La baja es lógica: el registro se conserva.
        </p>
        @if (errorBaja(); as e) {
          <p class="aviso error" role="alert">{{ e }}</p>
        }
      </app-dialogo-confirmacion>
    }
  `,
  styles: `
    .margen {
      margin: 0 24px 24px;
    }
    .cargando {
      padding: 24px;
      color: var(--tinta-2);
    }
  `,
})
export class ListadoPersonal implements OnInit {
  protected readonly config = configDeRuta();
  private readonly api = apiDeTipo(this.config.tipo);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly buscar = new FormControl('', { nonNullable: true });
  private readonly refresco = new Subject<void>();

  protected readonly filas = signal<ResumenDTO[]>([]);
  protected readonly cargando = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly aviso = signal<string | null>(null);
  protected readonly porEliminar = signal<ResumenDTO | null>(null);
  protected readonly eliminando = signal(false);
  protected readonly errorBaja = signal<string | null>(null);

  protected readonly columnas: ColumnaTabla[] = [
    { clave: 'titulo', titulo: 'Nombre' },
    { clave: 'subtitulo', titulo: 'Detalle' },
    { clave: 'estado', titulo: 'Estado' },
    { clave: 'acciones', titulo: 'Acciones' },
  ];

  protected textoVacio(): string {
    return this.buscar.value.trim()
      ? `Ningún ${this.config.singular} coincide con la búsqueda.`
      : `Aún no hay ${this.config.plural.toLowerCase()} registrados.`;
  }

  constructor() {
    const state = this.router.getCurrentNavigation()?.extras.state as
      { aviso?: string } | undefined;
    if (state?.aviso) this.aviso.set(state.aviso);
  }

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
          this.api.listar(f.trim()).pipe(
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

  protected activo(fila: ResumenDTO): boolean {
    return esActivo(fila.estado);
  }

  protected pedirBaja(fila: ResumenDTO): void {
    this.errorBaja.set(null);
    this.porEliminar.set(fila);
  }

  protected cancelarBaja(): void {
    this.porEliminar.set(null);
  }

  protected async confirmarBaja(): Promise<void> {
    const fila = this.porEliminar();
    if (!fila) return;
    this.eliminando.set(true);
    this.errorBaja.set(null);
    try {
      await firstValueFrom(this.api.eliminar(fila.id));
      this.porEliminar.set(null);
      this.aviso.set(`Se dio de baja a ${fila.titulo}.`);
      this.recargar();
    } catch (e) {
      const err = e as ErrorApi;
      this.errorBaja.set(err.mensaje);
      // Si ya no existe, el listado está desactualizado.
      if (err.estado === 404) this.recargar();
    } finally {
      this.eliminando.set(false);
    }
  }
}
