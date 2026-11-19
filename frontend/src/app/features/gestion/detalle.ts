import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ErrorApi } from '../../core/errores';
import { iniciales } from '../../layout/menu';
import { DialogoConfirmacion } from '../../shared/dialogo-confirmacion';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { camposDeDetalle, fechaCorta } from '../../shared/formato';
import { apiDeTipo, configDeRuta } from './personal';

/**
 * M-14 · Detalle de empleado o distribuidor (CU-CON-02). *Eliminar* abre la confirmación (EMP-04, DIS-04).
 * Solo muestra lo que trae el contrato: `DetalleDTO.campos` de EMPLEADO o DISTRIBUIDOR.
 */
@Component({
  selector: 'app-detalle-personal',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, EtiquetaEstado, DialogoConfirmacion],
  template: `
    <section class="pagina">
      <p class="migas">
        <a routerLink="/gestion">Inicio</a> /
        <a [routerLink]="config.ruta">{{ config.plural }}</a> / Detalle
      </p>

      @if (aviso(); as a) {
        <div class="aviso exito" role="status">{{ a }}</div>
      }

      @if (noEncontrado()) {
        <div class="aviso error" role="alert">
          <p>No encontramos {{ config.articulo }} {{ config.singular }} que buscas.</p>
          <a class="boton secundario volver" [routerLink]="config.ruta">Volver al listado</a>
        </div>
      } @else if (error(); as e) {
        <div class="aviso error" role="alert">
          <p>{{ e }}</p>
          <button type="button" class="boton secundario volver" (click)="cargar()">
            Reintentar
          </button>
        </div>
      } @else if (datos(); as d) {
        <header class="cabecera">
          <span class="avatar" aria-hidden="true">{{ iniciales(d['nombre']) }}</span>
          <div>
            <h1>{{ d['nombre'] }}</h1>
            <p class="subtitulo">{{ subtitulo() }}</p>
          </div>
          <div class="acciones-cabecera">
            <a class="boton secundario" [routerLink]="config.ruta + '/' + id + '/editar'">Editar</a>
            <button
              type="button"
              class="boton secundario peligro-borde"
              [disabled]="!activo()"
              (click)="pedirBaja()"
            >
              Eliminar
            </button>
          </div>
        </header>

        <div class="tarjetas">
          <section class="tarjeta" aria-labelledby="t-datos">
            <h2 id="t-datos">Datos</h2>
            <dl class="lista-datos">
              <dt>Documento</dt>
              <dd>{{ d['documento'] }}</dd>
              <dt>Correo</dt>
              <dd>{{ d['correo'] }}</dd>
              <dt>Teléfono</dt>
              <dd>{{ d['telefono'] }}</dd>
              <dt>Estado</dt>
              <dd>
                <app-etiqueta-estado [estado]="activo() ? 'ACTIVO' : 'INACTIVO'" />
              </dd>
            </dl>
          </section>

          @if (config.tipo === 'empleado') {
            <section class="tarjeta" aria-labelledby="t-cargo">
              <h2 id="t-cargo">Cargo</h2>
              <dl class="lista-datos">
                <dt>Cargo</dt>
                <dd>{{ d['rol'] }}</dd>
                <dt>Fecha de registro</dt>
                <dd>{{ fecha(d['fechaRegistro']) }}</dd>
              </dl>
            </section>
          } @else {
            <section class="tarjeta" aria-labelledby="t-codigo">
              <h2 id="t-codigo">Código y comisión</h2>
              <dl class="lista-datos">
                <dt>Código</dt>
                <dd>
                  <span class="codigo">{{ d['codigo'] }}</span>
                </dd>
                <dt>Categoría</dt>
                <dd>{{ d['categoria'] }}</dd>
                <dt>Referidos</dt>
                <dd>{{ d['referidos'] }}</dd>
              </dl>
            </section>
          }
        </div>

        <div>
          <a class="boton secundario" [routerLink]="config.ruta"
            ><span aria-hidden="true">←&nbsp;</span>Volver al listado</a
          >
        </div>
      } @else {
        <p role="status">Cargando…</p>
      }
    </section>

    @if (confirmando()) {
      <app-dialogo-confirmacion
        [titulo]="'Dar de baja ' + config.articulo + ' ' + config.singular"
        textoConfirmar="Dar de baja"
        [peligro]="true"
        [ocupado]="eliminando()"
        (confirmar)="confirmarBaja()"
        (cancelar)="confirmando.set(false)"
      >
        <p>
          ¿Quieres dar de baja a <strong>{{ datos()?.['nombre'] }}</strong
          >? La baja es lógica: queda inactivo y el registro se conserva.
        </p>
        @if (errorBaja(); as e) {
          <p class="aviso error" role="alert">{{ e }}</p>
        }
      </app-dialogo-confirmacion>
    }
  `,
  styles: `
    .cabecera {
      display: flex;
      align-items: center;
      gap: 20px;
    }
    .avatar {
      display: grid;
      flex-shrink: 0;
      place-items: center;
      width: 64px;
      height: 64px;
      font-size: 22px;
      font-weight: 700;
      color: var(--verde);
      background: var(--oro);
      border-radius: 50%;
    }
    .acciones-cabecera {
      display: flex;
      gap: 12px;
      margin-left: auto;
    }
    .peligro-borde {
      color: var(--rojo);
      border-color: var(--rojo);
    }
    .tarjetas {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 28px;
    }
    .tarjeta h2 {
      margin-bottom: 16px;
    }
    .volver {
      margin-top: 8px;
    }
    @media (max-width: 900px) {
      .tarjetas {
        grid-template-columns: minmax(0, 1fr);
      }
      .cabecera {
        flex-wrap: wrap;
      }
    }
  `,
})
export class DetallePersonal implements OnInit {
  protected readonly config = configDeRuta();
  private readonly api = apiDeTipo(this.config.tipo);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  protected readonly id = Number(this.route.snapshot.paramMap.get('id'));

  protected readonly datos = signal<Record<string, string> | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly noEncontrado = signal(false);
  protected readonly aviso = signal<string | null>(null);
  protected readonly confirmando = signal(false);
  protected readonly eliminando = signal(false);
  protected readonly errorBaja = signal<string | null>(null);

  protected readonly iniciales = iniciales;
  protected readonly fecha = fechaCorta;

  constructor() {
    const state = this.router.getCurrentNavigation()?.extras.state as
      { aviso?: string } | undefined;
    if (state?.aviso) this.aviso.set(state.aviso);
  }

  ngOnInit(): void {
    void this.cargar();
  }

  protected activo(): boolean {
    return this.datos()?.['activo'] === 'true';
  }

  protected subtitulo(): string {
    const d = this.datos();
    if (!d) return '';
    const tipo = this.config.tipo === 'empleado' ? 'Empleado' : 'Distribuidor';
    const anio = /^\d{4}/.exec(d['fechaRegistro'] ?? '')?.[0];
    if (!this.activo()) return `${tipo} · dado de baja`;
    return anio ? `${tipo} · activo desde ${anio}` : `${tipo} · activo`;
  }

  protected async cargar(): Promise<void> {
    this.error.set(null);
    this.noEncontrado.set(false);
    try {
      this.datos.set(camposDeDetalle(await firstValueFrom(this.api.detalle(this.id))));
    } catch (e) {
      const err = e as ErrorApi;
      if (err.estado === 404) this.noEncontrado.set(true);
      else this.error.set(err.mensaje);
    }
  }

  protected pedirBaja(): void {
    this.errorBaja.set(null);
    this.confirmando.set(true);
  }

  protected async confirmarBaja(): Promise<void> {
    this.eliminando.set(true);
    this.errorBaja.set(null);
    try {
      await firstValueFrom(this.api.eliminar(this.id));
      this.confirmando.set(false);
      this.aviso.set('Se dio de baja el registro.');
      await this.cargar();
    } catch (e) {
      this.errorBaja.set((e as ErrorApi).mensaje);
    } finally {
      this.eliminando.set(false);
    }
  }
}
