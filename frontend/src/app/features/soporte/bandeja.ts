import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  OnInit,
  signal,
  computed,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  catchError,
  distinctUntilChanged,
  firstValueFrom,
  map,
  merge,
  of,
  startWith,
  Subject,
  switchMap,
  tap,
} from 'rxjs';
import { ResumenDTO } from '../../core/api/dto';
import { SoporteApi } from '../../core/api/soporte.api';
import { ErrorApi } from '../../core/errores';
import { Campo } from '../../shared/campo';
import { etiquetaCategoria } from '../../shared/categoria-ticket';
import { campoDelError, ErroresCampo } from '../../shared/errores-formulario';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { fechaHoraCorta, fechaLarga, hoyIso } from '../../shared/formato';
import { noVacio } from '../../shared/formularios/validadores';
import { aTicket, nivelSiguiente, Ticket } from './ticket';

type CargaDetalle = { ticket: Ticket } | { error: ErrorApi } | null;

/**
 * M-17 · Bandeja de tickets (CU-SOP-02, CU-SOP-03). Lista del día a la izquierda
 * (`GET /tickets/diarios?fecha=`); al elegir uno, el detalle con movimientos, observación
 * obligatoria y *Marcar resuelto* / *Escalar de nivel* (`POST /tickets/{id}/enrutamiento`).
 */
@Component({
  selector: 'app-bandeja',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Campo, EtiquetaEstado],
  template: `
    <section class="pagina">
      <div class="encabezado-pagina">
        <div>
          <h1>Tickets del día</h1>
          <p class="subtitulo">
            {{ esHoy() ? 'Creados hoy' : 'Creados ese día' }} y abiertos de días anteriores ·
            {{ fechaTexto() }}
          </p>
        </div>
        <div class="campo selector-fecha">
          <label for="fecha">Fecha</label>
          <input id="fecha" type="date" [formControl]="fecha" [max]="hoy" />
        </div>
      </div>

      <div class="columnas">
        <div class="tarjeta sin-relleno">
          @if (errorLista(); as e) {
            <div class="aviso error margen" role="alert">
              <p>{{ e }}</p>
              <button type="button" class="boton secundario" (click)="recargarLista()">
                Reintentar
              </button>
            </div>
          } @else if (cargandoLista() && filas().length === 0) {
            <p class="cargando" role="status">Cargando tickets…</p>
          } @else {
            <div class="envoltura">
              <table>
                <caption class="solo-lector">
                  Tickets del día
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Ticket</th>
                    <th scope="col">Tipo</th>
                    <th scope="col">Nivel</th>
                    <th scope="col">Estado</th>
                  </tr>
                </thead>
                <tbody>
                  @for (f of filas(); track f.id) {
                    <tr [class.seleccionada]="f.id === id()" (click)="seleccionar(f.id)">
                      <td>
                        <a
                          class="num"
                          [routerLink]="['/soporte/tickets', f.id]"
                          [attr.aria-current]="f.id === id() ? 'true' : null"
                          >#{{ f.id }}<span class="solo-lector"> {{ tipo(f.titulo) }}</span></a
                        >
                      </td>
                      <td>{{ tipo(f.titulo) }}</td>
                      <td>{{ f.subtitulo }}</td>
                      <td><app-etiqueta-estado [estado]="f.estado" /></td>
                    </tr>
                  } @empty {
                    <tr>
                      <td class="vacio" colspan="4">No hay tickets para esta fecha.</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>

        <aside class="tarjeta detalle" aria-live="polite" aria-label="Detalle del ticket">
          @if (!id()) {
            <p class="seleccione">Selecciona un ticket de la lista para ver su detalle.</p>
          } @else if (cargandoDetalle() && !ticket()) {
            <p role="status">Cargando el ticket…</p>
          } @else if (errorDetalle(); as e) {
            <div class="aviso error" role="alert">{{ e }}</div>
          } @else if (ticket(); as t) {
            <div class="cabecera">
              <h2>Ticket #{{ t.id }}</h2>
              <app-etiqueta-estado [estado]="t.estado" [etiqueta]="resumenEstado(t)" />
            </div>
            <dl class="lista-datos">
              <dt>Reportado por</dt>
              <dd>{{ t.reportante }}</dd>
              <dt>Tipo</dt>
              <dd>{{ tipo(t.categoria) }}</dd>
              <dt>Sitio</dt>
              <dd>{{ t.sitio || '—' }}</dd>
              <dt>Fecha</dt>
              <dd>{{ fechaHora(t.fechaCreacion) }}</dd>
              <dt>Descripción</dt>
              <dd>{{ t.descripcion }}</dd>
            </dl>

            <div>
              <h3>Movimientos</h3>
              @if (t.movimientos.length === 0) {
                <p class="ayuda">Aún no tiene movimientos.</p>
              } @else {
                <ol class="movimientos">
                  @for (m of t.movimientos; track $index) {
                    <li>
                      <span class="cuando">{{ m.fecha }} · {{ m.responsable }}</span>
                      <span
                        ><strong>{{ m.estado }}</strong> en nivel {{ m.nivel }}:
                        {{ m.observacion }}</span
                      >
                    </li>
                  }
                </ol>
              }
            </div>

            @if (aviso(); as a) {
              <div class="aviso exito" role="status">{{ a }}</div>
            }
            @if (errorAccion(); as e) {
              <div class="aviso error" role="alert"><span aria-hidden="true">⚠ </span>{{ e }}</div>
            }

            @if (t.estado === 'RESUELTO') {
              <p class="aviso advertencia" role="status">
                Este ticket ya está resuelto; no admite más cambios de nivel.
              </p>
            } @else {
              <form [formGroup]="form" (ngSubmit)="enrutar(false)" novalidate>
                <app-campo
                  nombre="observacion"
                  etiqueta="Observación"
                  tipo="textarea"
                  [filas]="3"
                  placeholder="Caché del servidor saturada; se requiere revisión de gestión."
                  [control]="form.controls.observacion"
                  [errorServidor]="errores.de('observacion')"
                />
                <div class="acciones">
                  <button type="submit" class="boton" [disabled]="enviando()">
                    Marcar resuelto
                  </button>
                  <button
                    type="button"
                    class="boton oro"
                    [disabled]="enviando() || !siguiente()"
                    (click)="enrutar(true)"
                  >
                    {{ siguiente() ? 'Escalar a ' + siguiente() : 'Escalar de nivel' }}
                  </button>
                </div>
                @if (!siguiente()) {
                  <p class="ayuda">
                    El ticket ya está en el último nivel de servicio ({{ t.nivel }}); solo puede
                    resolverse.
                  </p>
                }
              </form>
            }
            <p class="ayuda">
              La comunicación entre niveles ocurre por fuera del sistema; aquí solo se registra el
              cambio de estado.
            </p>
          }
        </aside>
      </div>
    </section>
  `,
  styles: `
    .selector-fecha {
      min-width: 190px;
    }
    .columnas {
      display: grid;
      grid-template-columns: minmax(0, 6fr) minmax(0, 5fr);
      gap: 28px;
      align-items: start;
    }
    .envoltura {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th {
      padding: 14px 20px;
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-align: left;
      text-transform: uppercase;
      color: var(--tinta-2);
      background: #fafbfa;
      border-bottom: 1px solid var(--linea);
    }
    td {
      padding: 16px 20px;
      border-bottom: 1px solid var(--linea);
    }
    tbody tr:not(:has(.vacio)) {
      cursor: pointer;
    }
    tbody tr:not(:has(.vacio)):hover {
      background: #f7faf9;
    }
    tbody tr.seleccionada {
      background: var(--verde-claro);
    }
    .num {
      color: var(--tinta);
      text-decoration: none;
    }
    tr.seleccionada .num {
      font-weight: 700;
    }
    .vacio {
      padding: 36px 20px;
      text-align: center;
      color: var(--tinta-2);
    }
    .margen {
      margin: 24px;
    }
    .cargando {
      padding: 24px;
      color: var(--tinta-2);
    }
    .detalle {
      display: flex;
      flex-direction: column;
      gap: 18px;
      padding: 28px;
    }
    .cabecera {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }
    h3 {
      margin-bottom: 8px;
      font-size: 15px;
    }
    .seleccione {
      padding: 24px 0;
      text-align: center;
      color: var(--tinta-2);
    }
    .movimientos {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .movimientos li {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding-left: 12px;
      border-left: 3px solid var(--linea);
    }
    .cuando {
      font-size: 13px;
      color: var(--tinta-2);
    }
    form {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .acciones {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    .boton.oro {
      color: var(--tinta);
      background: var(--oro);
      border-color: var(--oro);
    }
    .boton.oro:hover:not(:disabled) {
      background: #e4a82f;
    }
    .ayuda {
      font-size: 13px;
      color: var(--tinta-2);
    }
    @media (max-width: 1100px) {
      .columnas {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class Bandeja implements OnInit {
  private readonly api = inject(SoporteApi);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly hoy = hoyIso();
  protected readonly fecha = new FormControl(this.hoy, { nonNullable: true });
  private readonly fechaElegida = toSignal(this.fecha.valueChanges.pipe(startWith(this.hoy)), {
    initialValue: this.hoy,
  });
  protected readonly esHoy = computed(() => this.fechaElegida() === this.hoy);
  protected readonly fechaTexto = computed(() => fechaLarga(this.fechaElegida() || this.hoy));

  /** Identificador de la ruta `/soporte/tickets/:id`. */
  private readonly id$ = this.route.paramMap.pipe(
    map((p) => {
      const v = Number(p.get('id'));
      return p.get('id') !== null && Number.isInteger(v) ? v : null;
    }),
    distinctUntilChanged(),
  );
  protected readonly id = toSignal(this.id$, { initialValue: null });

  protected readonly filas = signal<ResumenDTO[]>([]);
  protected readonly cargandoLista = signal(true);
  protected readonly errorLista = signal<string | null>(null);
  private readonly refrescoLista = new Subject<void>();

  private readonly carga = signal<CargaDetalle>(null);
  protected readonly cargandoDetalle = signal(false);
  protected readonly ticket = computed(() => {
    const c = this.carga();
    return c && 'ticket' in c ? c.ticket : null;
  });
  protected readonly errorDetalle = computed(() => {
    const c = this.carga();
    return c && 'error' in c ? c.error.mensaje : null;
  });
  private readonly refrescoDetalle = new Subject<void>();

  protected readonly siguiente = computed(() => {
    const t = this.ticket();
    return t && t.estado !== 'RESUELTO' ? nivelSiguiente(t.nivel) : null;
  });

  protected readonly form = new FormGroup({
    observacion: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, noVacio],
    }),
  });
  protected readonly errores = new ErroresCampo([this.form]);
  protected readonly enviando = signal(false);
  protected readonly aviso = signal<string | null>(null);
  protected readonly errorAccion = signal<string | null>(null);

  ngOnInit(): void {
    // Lista: cambia con la fecha o al refrescar.
    merge(
      this.fecha.valueChanges.pipe(startWith(this.hoy), distinctUntilChanged()),
      this.refrescoLista.pipe(map(() => this.fecha.value)),
    )
      .pipe(
        map((f) => f || this.hoy),
        tap(() => {
          this.cargandoLista.set(true);
          this.errorLista.set(null);
        }),
        switchMap((f) =>
          this.api.diarios(f).pipe(
            catchError((e: ErrorApi) => {
              this.errorLista.set(e.mensaje);
              return of<ResumenDTO[]>([]);
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((lista) => {
        this.filas.set(lista);
        this.cargandoLista.set(false);
      });

    // Detalle: cambia con el id de la ruta o al refrescar.
    merge(
      this.id$.pipe(
        tap(() => {
          this.carga.set(null);
          this.form.reset();
        }),
      ),
      this.refrescoDetalle.pipe(map(() => this.id())),
    )
      .pipe(
        tap(() => {
          this.aviso.set(null);
          this.errorAccion.set(null);
          this.errores.limpiar();
        }),
        switchMap((id) => {
          if (id === null) return of<CargaDetalle>(null);
          this.cargandoDetalle.set(true);
          return this.api.detalle(id).pipe(
            map((d): CargaDetalle => ({ ticket: aTicket(d) })),
            catchError((error: ErrorApi) => of<CargaDetalle>({ error })),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((c) => {
        this.carga.set(c);
        this.cargandoDetalle.set(false);
      });
  }

  protected recargarLista(): void {
    this.refrescoLista.next();
  }

  protected seleccionar(id: number): void {
    if (id !== this.id()) {
      void this.router.navigate(['/soporte/tickets', id]);
    }
  }

  protected tipo(literal: string): string {
    return etiquetaCategoria(literal);
  }

  protected resumenEstado(t: Ticket): string {
    const e = t.estado.charAt(0) + t.estado.slice(1).toLowerCase();
    return `${e} · Nivel ${t.nivel}`;
  }

  protected fechaHora(iso: string): string {
    return fechaHoraCorta(iso);
  }

  protected async enrutar(escalar: boolean): Promise<void> {
    const t = this.ticket();
    if (!t) return;
    this.aviso.set(null);
    this.errorAccion.set(null);
    this.errores.limpiar();
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    const destino = this.siguiente();
    try {
      await firstValueFrom(
        this.api.enrutar(t.id, {
          escalar,
          observacion: this.form.controls.observacion.value.trim(),
        }),
      );
      this.form.reset();
      this.refrescoDetalle.next();
      this.refrescoLista.next();
      // El aviso se fija después del refresco porque este lo limpia.
      queueMicrotask(() =>
        this.aviso.set(
          escalar
            ? `Ticket #${t.id} escalado a ${destino}.`
            : `Ticket #${t.id} marcado como resuelto.`,
        ),
      );
    } catch (e) {
      const err = e as ErrorApi;
      const campo = campoDelError(err);
      if (campo && campo in this.form.controls) {
        this.errores.fijar(campo, err.mensaje);
      } else if (err.codigo !== 'CONTINGENCIA') {
        queueMicrotask(() => this.errorAccion.set(err.mensaje));
        // 409 y 404: el ticket cambió; se vuelve a leer para mostrar su estado actual.
        if (err.estado === 409 || err.estado === 404) {
          this.refrescoDetalle.next();
          this.refrescoLista.next();
        }
      }
    } finally {
      this.enviando.set(false);
    }
  }
}
