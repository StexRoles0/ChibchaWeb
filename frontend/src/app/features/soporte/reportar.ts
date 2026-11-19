import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ClientesApi } from '../../core/api/clientes.api';
import { ResumenDTO } from '../../core/api/dto';
import { SoporteApi } from '../../core/api/soporte.api';
import { SesionStore } from '../../core/auth/sesion.store';
import { ErrorApi } from '../../core/errores';
import { Campo, OpcionCampo } from '../../shared/campo';
import { campoDelError, ErroresCampo } from '../../shared/errores-formulario';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { CATEGORIAS_TICKET, etiquetaCategoria } from '../../shared/categoria-ticket';
import { noVacio } from '../../shared/formularios/validadores';
import { CeldaTabla, ColumnaTabla, Tabla } from '../../shared/tabla';

/**
 * M-10 · Reportar una novedad (CU-SOP-01). Pantalla compartida: el cliente elige además el sitio
 * afectado (`GET /clientes/me/sitios`, P-06); los empleados no. Abajo, `GET /tickets/mios`.
 */
@Component({
  selector: 'app-reportar-novedad',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Campo, Tabla, CeldaTabla, EtiquetaEstado],
  template: `
    <section class="pagina">
      <div>
        <p class="migas"><a [routerLink]="inicio()">Inicio</a> / Soporte</p>
        <h1>Reportar una novedad</h1>
        <p class="subtitulo">El nivel de servicio inicial lo asigna el sistema.</p>
      </div>

      <div class="columnas">
        <form class="tarjeta" [formGroup]="form" (ngSubmit)="enviar()" novalidate>
          <app-campo
            nombre="categoria"
            etiqueta="Tipo de novedad"
            tipo="select"
            [opciones]="categorias"
            [control]="form.controls.categoria"
            [errorServidor]="errores.de('categoria')"
          />
          @if (esCliente()) {
            <app-campo
              nombre="idSitio"
              etiqueta="Sitio afectado (opcional)"
              tipo="select"
              opcionVacia="Ninguno en particular"
              [opciones]="sitios()"
              [control]="form.controls.idSitio"
              [errorServidor]="errores.de('idSitio')"
              [ayuda]="errorSitios() ?? ''"
            />
          }
          <app-campo
            nombre="descripcion"
            etiqueta="Describe el problema"
            tipo="textarea"
            [filas]="5"
            placeholder="El sitio tarda más de 10 segundos en cargar desde esta mañana."
            [control]="form.controls.descripcion"
            [errorServidor]="errores.de('descripcion')"
          />

          @if (creado(); as id) {
            <div class="aviso exito" role="status">
              Ticket <strong>#{{ id }}</strong> registrado. Quedó abierto en el nivel de soporte
              inicial.
            </div>
          }
          @if (errorGeneral(); as e) {
            <div class="aviso error" role="alert"><span aria-hidden="true">⚠ </span>{{ e }}</div>
          }

          <button type="submit" class="boton ancho" [disabled]="enviando()">
            {{ enviando() ? 'Enviando…' : 'Enviar ticket' }}
          </button>
        </form>

        <div class="tarjeta sin-relleno">
          <h2 class="titulo-tabla">Mis tickets</h2>
          @if (errorLista(); as e) {
            <div class="aviso error margen" role="alert">
              <p>{{ e }}</p>
              <button type="button" class="boton secundario" (click)="cargar()">Reintentar</button>
            </div>
          } @else if (cargando() && filas().length === 0) {
            <p class="cargando" role="status">Cargando tus tickets…</p>
          } @else {
            <app-tabla
              [columnas]="columnasTabla"
              [filas]="filas()"
              descripcion="Mis tickets"
              textoVacio="Todavía no has reportado ninguna novedad."
            >
              <ng-template appCelda let-fila let-columna="columna">
                @switch (columna.clave) {
                  @case ('id') {
                    #{{ fila.id }}
                  }
                  @case ('titulo') {
                    {{ tipo(fila.titulo) }}
                  }
                  @case ('estado') {
                    <app-etiqueta-estado [estado]="fila.estado" />
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
      gap: 18px;
      padding: 28px 32px;
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
export class ReportarNovedad implements OnInit {
  private readonly soporte = inject(SoporteApi);
  private readonly clientes = inject(ClientesApi);
  private readonly sesion = inject(SesionStore);

  protected readonly esCliente = this.sesion.esCliente;
  protected readonly inicio = computed(() =>
    this.esCliente() ? '/cliente' : this.sesion.rutaInicio(),
  );

  protected readonly categorias: OpcionCampo[] = CATEGORIAS_TICKET;
  protected readonly form = new FormGroup({
    categoria: new FormControl(CATEGORIAS_TICKET[0].valor, {
      nonNullable: true,
      validators: Validators.required,
    }),
    idSitio: new FormControl('', { nonNullable: true }),
    descripcion: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, noVacio],
    }),
  });
  protected readonly errores = new ErroresCampo([this.form]);

  protected readonly columnasTabla: ColumnaTabla[] = [
    { clave: 'id', titulo: 'Ticket' },
    { clave: 'titulo', titulo: 'Tipo' },
    { clave: 'subtitulo', titulo: 'Nivel' },
    { clave: 'estado', titulo: 'Estado' },
  ];

  protected readonly sitios = signal<OpcionCampo[]>([]);
  protected readonly errorSitios = signal<string | null>(null);
  protected readonly filas = signal<ResumenDTO[]>([]);
  protected readonly cargando = signal(true);
  protected readonly errorLista = signal<string | null>(null);
  protected readonly enviando = signal(false);
  protected readonly errorGeneral = signal<string | null>(null);
  protected readonly creado = signal<number | null>(null);

  protected tipo(literal: string): string {
    return etiquetaCategoria(literal);
  }

  ngOnInit(): void {
    void this.cargar();
    if (this.esCliente()) void this.cargarSitios();
    this.form.valueChanges.subscribe(() => this.creado.set(null));
  }

  private async cargarSitios(): Promise<void> {
    try {
      const lista = await firstValueFrom(this.clientes.sitios());
      this.sitios.set(lista.map((s) => ({ valor: String(s.id), etiqueta: s.titulo })));
    } catch {
      this.errorSitios.set('No pudimos cargar tus sitios; puedes enviar el ticket sin elegir uno.');
    }
  }

  protected async cargar(): Promise<void> {
    this.cargando.set(true);
    this.errorLista.set(null);
    try {
      this.filas.set(await firstValueFrom(this.soporte.mios()));
    } catch (e) {
      this.errorLista.set((e as ErrorApi).mensaje);
    } finally {
      this.cargando.set(false);
    }
  }

  protected async enviar(): Promise<void> {
    this.errorGeneral.set(null);
    this.errores.limpiar();
    this.creado.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    try {
      const v = this.form.getRawValue();
      const r = await firstValueFrom(
        this.soporte.crear({
          categoria: v.categoria,
          descripcion: v.descripcion.trim(),
          ...(this.esCliente() && v.idSitio ? { idSitio: Number(v.idSitio) } : {}),
        }),
      );
      this.form.reset({ categoria: v.categoria, idSitio: '', descripcion: '' });
      this.creado.set(r.id);
      await this.cargar();
    } catch (e) {
      const err = e as ErrorApi;
      const campo = campoDelError(err);
      if (campo && campo in this.form.controls) this.errores.fijar(campo, err.mensaje);
      else if (err.codigo !== 'CONTINGENCIA') this.errorGeneral.set(err.mensaje);
    } finally {
      this.enviando.set(false);
    }
  }
}
