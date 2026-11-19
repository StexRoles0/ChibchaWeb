import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SesionStore } from '../../core/auth/sesion.store';
import { EtiquetaEstado } from '../../shared/etiqueta-estado';
import { fechaCorta, primerNombre } from '../../shared/formato';
import { MontoPipe } from '../../shared/monto';
import { PerfilStore } from './perfil.store';

/** M-05 · Inicio del cliente. Todo sale de `GET /clientes/me`. */
@Component({
  selector: 'app-inicio-cliente',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, EtiquetaEstado, MontoPipe],
  template: `
    <section class="pagina">
      <div>
        <h1>Hola, {{ saludo() }}</h1>
        <p class="subtitulo">Este es el estado de tu hospedaje.</p>
      </div>

      @if (store.error(); as e) {
        <div class="aviso error" role="alert">
          <p>{{ e }}</p>
          <button type="button" class="boton secundario reintento" (click)="store.cargar()">
            Reintentar
          </button>
        </div>
      } @else if (store.perfil(); as p) {
        <div class="resumen">
          <article class="tarjeta">
            <h2 class="rotulo">Sitio web</h2>
            <p class="valor sitio">{{ p.sitio }}</p>
            <app-etiqueta-estado
              [estado]="p.activo ? 'ACTIVO' : 'INACTIVO'"
              [etiqueta]="p.activo ? 'Activo' : 'Inactivo'"
            />
          </article>
          <article class="tarjeta">
            <h2 class="rotulo">Paquete y plan</h2>
            <p class="valor">{{ p.paquete }}</p>
            <p class="detalle">Plan {{ p.plan.toLowerCase() }} · {{ p.montoPeriodo | monto }}</p>
          </article>
          <article class="tarjeta">
            <h2 class="rotulo">Próximo cobro</h2>
            <p class="valor">{{ fechaCorta(p.fechaCorte) }}</p>
            <p class="detalle">{{ p.tarjeta }}</p>
          </article>
        </div>
      } @else {
        <p role="status">Cargando tu información…</p>
      }

      <nav class="atajos" aria-label="Atajos">
        <a class="tarjeta atajo" routerLink="/cliente/perfil">
          <span class="ficha" aria-hidden="true">P</span>
          <span>
            <strong>Mi perfil</strong>
            <span class="detalle">Modificar o eliminar tus datos</span>
          </span>
          <span class="flecha" aria-hidden="true">→</span>
        </a>
        <a class="tarjeta atajo" routerLink="/cliente/dominios">
          <span class="ficha" aria-hidden="true">D</span>
          <span>
            <strong>Dominios</strong>
            <span class="detalle">Solicitar el registro de un dominio propio</span>
          </span>
          <span class="flecha" aria-hidden="true">→</span>
        </a>
        <a class="tarjeta atajo" routerLink="/cliente/soporte">
          <span class="ficha" aria-hidden="true">S</span>
          <span>
            <strong>Soporte</strong>
            <span class="detalle">Reportar una novedad de tu sitio</span>
          </span>
          <span class="flecha" aria-hidden="true">→</span>
        </a>
      </nav>
    </section>
  `,
  styleUrl: './inicio.scss',
})
export class InicioCliente implements OnInit {
  protected readonly store = inject(PerfilStore);
  private readonly sesion = inject(SesionStore);
  protected readonly fechaCorta = fechaCorta;

  protected saludo(): string {
    return primerNombre(this.sesion.nombre());
  }

  ngOnInit(): void {
    void this.store.cargar();
  }
}
