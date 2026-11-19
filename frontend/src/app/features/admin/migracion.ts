import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DialogoConfirmacion } from '../../shared/dialogo-confirmacion';
import { MigracionStore } from './migracion.store';

interface Paso {
  texto: string;
  estado: 'hecho' | 'pendiente' | 'fallido';
}

/**
 * M-19 · Migración de datos legados (CU-MIG-01). Fase 1: simular y revisar el log.
 * Fase 2: ejecutar la migración real o cancelar. Las transiciones son las de RN-25 a RN-27.
 */
@Component({
  selector: 'app-migracion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, DialogoConfirmacion],
  template: `
    <section class="pagina">
      <div>
        <p class="migas"><a routerLink="/admin">Administración</a> / Migración</p>
        <h1>Migración de datos legados</h1>
        <p class="subtitulo">Ejecuta primero la simulación y revisa el log antes de confirmar.</p>
      </div>

      <div class="barra-pasos">
        <ol class="pasos" aria-label="Fases de la migración">
          @for (p of pasos(); track $index) {
            <li
              class="paso"
              [class]="p.estado"
              [attr.aria-current]="actual() === $index ? 'step' : null"
            >
              {{ p.texto }}
              @if (p.estado === 'hecho') {
                <span class="solo-lector">(completado)</span>
              } @else if (p.estado === 'fallido') {
                <span class="solo-lector">(fallido)</span>
              }
            </li>
            @if (!$last) {
              <li class="flecha" aria-hidden="true">→</li>
            }
          }
        </ol>
        @if (store.proceso()) {
          <button
            type="button"
            class="boton secundario"
            [disabled]="store.ocupado() !== null"
            (click)="store.simular()"
          >
            {{ store.ocupado() === 'simulando' ? 'Simulando…' : 'Ejecutar simulación de nuevo' }}
          </button>
        }
      </div>

      @if (store.error(); as e) {
        <div class="aviso error" role="alert"><span aria-hidden="true">⚠ </span>{{ e }}</div>
      }
      @switch (store.resultado()) {
        @case ('EJECUTADA') {
          <div class="aviso exito" role="status">
            Migración ejecutada: se escribieron {{ numero(proceso()?.validos) }} registros válidos
            (clientes, suscripciones y pagos). Los clientes migrados vinculan su cuenta en su primer
            ingreso.
          </div>
        }
        @case ('REVERTIDA') {
          <div class="aviso error" role="alert">
            La migración quedó revertida: una escritura falló (por ejemplo, un correo o subdominio
            que ya existe) y no se aplicó ningún cambio. Puedes ejecutar la simulación de nuevo.
          </div>
        }
        @case ('CANCELADA') {
          <div class="aviso advertencia" role="status">
            Migración cancelada. No se escribió ningún dato.
          </div>
        }
      }

      @if (!store.proceso()) {
        <div class="tarjeta vacio">
          <h2>Aún no hay una simulación</h2>
          <p>
            La simulación lee el sistema legado, valida cada registro y escribe el resultado en el
            log. No escribe datos de negocio.
          </p>
          <button
            type="button"
            class="boton"
            [disabled]="store.ocupado() !== null"
            (click)="store.simular()"
          >
            {{ store.ocupado() === 'simulando' ? 'Simulando…' : 'Ejecutar simulación' }}
          </button>
        </div>
      } @else if (store.proceso(); as p) {
        <div class="resumen">
          @for (r of store.resumen(); track r.tipo) {
            <article class="tarjeta">
              <h2 class="rotulo">{{ r.titulo }}</h2>
              <p class="cifra">{{ numero(r.validos) }} / {{ numero(r.leidos) }}</p>
              <p class="detalle">válidos / leídos</p>
            </article>
          }
        </div>

        <div class="log" role="region" aria-label="Log de la simulación" tabindex="0">
          <table>
            <caption class="solo-lector">
              Log de la simulación:
              {{
                p.validos
              }}
              válidos y
              {{
                p.invalidos
              }}
              inválidos
            </caption>
            <thead class="solo-lector">
              <tr>
                <th scope="col">Nivel</th>
                <th scope="col">Tipo</th>
                <th scope="col">Id legado</th>
                <th scope="col">Mensaje</th>
              </tr>
            </thead>
            <tbody>
              @for (e of p.entradas; track $index) {
                <tr [class]="nivelClase(e.nivel)">
                  <td class="nivel">{{ e.nivel }}</td>
                  <td>{{ e.tipo }}</td>
                  <td>{{ e.idLegado }}</td>
                  <td>{{ e.mensaje }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="4">La simulación no produjo entradas.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <p class="totales" role="status">
          {{ numero(p.validos) }} registros válidos · {{ numero(p.invalidos) }} inválidos (no se
          migrarán).
        </p>

        <div class="acciones">
          <button
            type="button"
            class="boton secundario peligro-borde"
            [disabled]="!store.puedeEjecutar()"
            (click)="dialogo.set('cancelar')"
          >
            Cancelar migración
          </button>
          <button
            type="button"
            class="boton"
            [disabled]="!store.puedeEjecutar()"
            (click)="dialogo.set('ejecutar')"
          >
            Ejecutar migración real
          </button>
        </div>
      }
    </section>

    @if (dialogo() === 'ejecutar') {
      <app-dialogo-confirmacion
        titulo="Ejecutar la migración real"
        textoConfirmar="Ejecutar migración"
        [ocupado]="store.ocupado() === 'confirmando'"
        (confirmar)="confirmar()"
        (cancelar)="dialogo.set(null)"
      >
        <p>
          Se escribirán {{ numero(proceso()?.validos) }} registros válidos en una sola transacción
          (clientes, suscripciones y pagos). Si cualquier escritura falla, se revierte todo. Los
          {{ numero(proceso()?.invalidos) }} inválidos no se migran.
        </p>
      </app-dialogo-confirmacion>
    }
    @if (dialogo() === 'cancelar') {
      <app-dialogo-confirmacion
        titulo="Cancelar la migración"
        textoConfirmar="Cancelar migración"
        textoCancelar="Volver"
        [peligro]="true"
        [ocupado]="store.ocupado() === 'cancelando'"
        (confirmar)="cancelarProceso()"
        (cancelar)="dialogo.set(null)"
      >
        <p>
          La simulación se descarta y no se escribe ningún dato. Para migrar tendrás que simular de
          nuevo.
        </p>
      </app-dialogo-confirmacion>
    }
  `,
  styles: `
    .barra-pasos {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }
    .pasos {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .paso {
      padding: 6px 14px;
      font-weight: 600;
      color: var(--tinta-2);
      background: #eceff0;
      border-radius: 999px;
    }
    .paso.hecho {
      color: var(--verde);
      background: var(--verde-claro);
    }
    .paso.fallido {
      color: var(--rojo);
      background: var(--rojo-claro);
    }
    .flecha {
      color: var(--tinta-2);
    }
    .vacio {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
      padding: 28px 32px;
      p {
        color: var(--tinta-2);
        max-width: 640px;
      }
    }
    .resumen {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 28px;
    }
    .rotulo {
      font-size: 14px;
      font-weight: 400;
      color: var(--tinta-2);
    }
    .cifra {
      margin-top: 8px;
      font-size: 32px;
      font-weight: 700;
    }
    .detalle {
      color: var(--tinta-2);
    }
    .log {
      max-height: 270px;
      overflow: auto;
      padding: 18px 24px;
      font-family: ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;
      font-size: 13.5px;
      color: #dfe8e4;
      background: #111c18;
      border-radius: 14px;
    }
    .log table {
      width: 100%;
      border-collapse: collapse;
    }
    .log td {
      padding: 3px 14px 3px 0;
      vertical-align: top;
    }
    .log td.nivel {
      width: 1%;
      font-weight: 700;
      white-space: nowrap;
    }
    .log tr.info .nivel {
      color: #7fd6b8;
    }
    .log tr.advertencia {
      color: #f0c36a;
    }
    .log tr.error {
      color: #ff9b8f;
    }
    .totales {
      color: var(--tinta-2);
    }
    .acciones {
      display: flex;
      justify-content: flex-end;
      gap: 14px;
    }
    .peligro-borde {
      color: var(--rojo);
      border-color: var(--rojo);
    }
    @media (max-width: 1100px) {
      .resumen {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class Migracion {
  protected readonly store = inject(MigracionStore);
  protected readonly proceso = this.store.proceso;
  protected readonly dialogo = signal<'ejecutar' | 'cancelar' | null>(null);

  /** Pasos de RN-25: simulación → aprobación → ejecución real. */
  protected readonly pasos = computed<Paso[]>(() => {
    const p = this.store.proceso();
    const e = p?.estado;
    if (!p) {
      return [
        { texto: '1 · Simulación', estado: 'pendiente' },
        { texto: '2 · Aprobación', estado: 'pendiente' },
        { texto: '3 · Ejecución real', estado: 'pendiente' },
      ];
    }
    if (e === 'CANCELADA') {
      return [
        { texto: '1 · Simulación completada', estado: 'hecho' },
        { texto: '2 · Aprobación', estado: 'pendiente' },
        { texto: '3 · Migración cancelada', estado: 'fallido' },
      ];
    }
    return [
      { texto: '1 · Simulación completada', estado: 'hecho' },
      {
        texto: '2 · Aprobación',
        estado: e === 'EJECUTADA' || e === 'REVERTIDA' ? 'hecho' : 'pendiente',
      },
      {
        texto:
          e === 'EJECUTADA'
            ? '3 · Ejecución real completada'
            : e === 'REVERTIDA'
              ? '3 · Ejecución revertida'
              : '3 · Ejecución real',
        estado: e === 'EJECUTADA' ? 'hecho' : e === 'REVERTIDA' ? 'fallido' : 'pendiente',
      },
    ];
  });
  /** Índice del paso en curso, para `aria-current`. */
  protected readonly actual = computed(() => {
    const e = this.store.proceso()?.estado;
    return !e ? 0 : e === 'SIMULADA' ? 1 : -1;
  });

  protected numero(n: number | undefined): string {
    return (n ?? 0).toLocaleString('es-CO');
  }

  protected nivelClase(nivel: string): string {
    return nivel === 'ERROR' ? 'error' : nivel === 'ADVERTENCIA' ? 'advertencia' : 'info';
  }

  protected async confirmar(): Promise<void> {
    await this.store.confirmar();
    this.dialogo.set(null);
  }

  protected async cancelarProceso(): Promise<void> {
    await this.store.cancelar();
    this.dialogo.set(null);
  }
}
