import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ContingenciaApi } from '../../core/api/contingencia.api';
import { SesionStore } from '../../core/auth/sesion.store';

/**
 * M-18 · Inicio del administrador. "Estado del sistema" solo muestra lo que el contrato permite
 * derivar: los eventos en respaldo salen de `GET /contingencia/pendientes`. El estado de la base
 * de datos y la última migración no tienen endpoint, así que no se muestran.
 */
@Component({
  selector: 'app-inicio-admin',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="pagina">
      <div>
        <h1>Administración</h1>
        <p class="subtitulo">Operaciones técnicas del sistema.</p>
      </div>

      <nav class="rejilla" aria-label="Atajos">
        @if (puedeMigrar) {
          <a class="tarjeta atajo" routerLink="/admin/migracion">
            <span class="ficha" aria-hidden="true">M</span>
            <span>
              <strong>Migración de datos legados</strong>
              <span class="detalle">Simular, revisar el log y ejecutar la migración real</span>
            </span>
            <span class="flecha" aria-hidden="true">→</span>
          </a>
        }
        @if (puedeContingencia) {
          <a class="tarjeta atajo" routerLink="/admin/contingencia">
            <span class="ficha" aria-hidden="true">C</span>
            <span>
              <strong>Contingencia</strong>
              <span class="detalle">Algoritmo de cifrado y sincronización del respaldo</span>
            </span>
            <span class="flecha" aria-hidden="true">→</span>
          </a>
        }
      </nav>

      @if (puedeContingencia) {
        <section class="tarjeta" aria-labelledby="estado-titulo">
          <h2 id="estado-titulo">Estado del sistema</h2>
          <div class="dato">
            <p class="rotulo">Eventos en respaldo</p>
            <p class="cifra" [attr.aria-busy]="eventos() === null">{{ texto() }}</p>
            @if (eventos() === 'error') {
              <p class="detalle">No se pudo consultar el respaldo.</p>
            } @else if (eventos() !== null && eventos() !== 0) {
              <a routerLink="/admin/contingencia">Ver y sincronizar</a>
            }
          </div>
        </section>
      }
    </section>
  `,
  styles: `
    .rejilla {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 28px;
    }
    .atajo {
      display: flex;
      align-items: flex-start;
      gap: 16px;
      color: inherit;
      text-decoration: none;
      &:hover {
        border-color: var(--verde-2);
      }
      strong {
        display: block;
        font-size: 17px;
      }
    }
    .detalle,
    .rotulo {
      color: var(--tinta-2);
    }
    .ficha {
      display: grid;
      flex-shrink: 0;
      place-items: center;
      width: 44px;
      height: 44px;
      font-weight: 700;
      color: var(--verde);
      background: var(--verde-claro);
      border-radius: 10px;
    }
    .flecha {
      margin-left: auto;
      color: var(--verde-2);
    }
    .dato {
      margin-top: 14px;
    }
    .cifra {
      margin: 4px 0;
      font-size: 32px;
      font-weight: 700;
    }
    @media (max-width: 1100px) {
      .rejilla {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class InicioAdmin implements OnInit {
  private readonly sesion = inject(SesionStore);
  private readonly contingencia = inject(ContingenciaApi);

  protected readonly puedeMigrar = this.sesion.tieneOperacion('MIGRAR_DATOS');
  protected readonly puedeContingencia = this.sesion.tieneOperacion('GESTIONAR_CONTINGENCIA');

  /** Número de eventos, `null` mientras carga o `'error'`. */
  protected readonly eventos = signal<number | null | 'error'>(null);

  async ngOnInit(): Promise<void> {
    if (!this.puedeContingencia) return;
    try {
      this.eventos.set((await firstValueFrom(this.contingencia.pendientes())).length);
    } catch {
      this.eventos.set('error');
    }
  }

  protected texto(): string {
    const e = this.eventos();
    if (e === null) return '…';
    return e === 'error' ? '—' : e.toLocaleString('es-CO');
  }
}
