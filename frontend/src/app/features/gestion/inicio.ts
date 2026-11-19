import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConsultasApi } from '../../core/api/consultas.api';
import { DistribuidoresApi } from '../../core/api/distribuidores.api';
import { ResumenDTO } from '../../core/api/dto';
import { EmpleadosApi } from '../../core/api/empleados.api';
import { SesionStore } from '../../core/auth/sesion.store';
import { esActivo } from './personal';

/** Conteo de activos: número, `null` mientras carga o `'error'` si la consulta falló. */
type Conteo = number | null | 'error';

/**
 * M-11 · Inicio de gestión. Los contadores se derivan de los listados del contrato
 * (`GET /empleados`, `GET /distribuidores`, `GET /consultas/CLIENTE`) contando los activos.
 */
@Component({
  selector: 'app-inicio-gestion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="pagina">
      <div>
        <h1>Panel de gestión</h1>
        <p class="subtitulo">Administra el personal, los distribuidores y consulta los clientes.</p>
      </div>

      <div class="rejilla" role="list" aria-label="Resumen">
        @if (puedeEmpleados) {
          <article class="tarjeta" role="listitem">
            <h2 class="rotulo">Empleados activos</h2>
            <p class="cifra" [attr.aria-busy]="empleados() === null">{{ texto(empleados()) }}</p>
          </article>
        }
        @if (puedeDistribuidores) {
          <article class="tarjeta" role="listitem">
            <h2 class="rotulo">Distribuidores activos</h2>
            <p class="cifra" [attr.aria-busy]="distribuidores() === null">
              {{ texto(distribuidores()) }}
            </p>
          </article>
        }
        @if (puedeClientes) {
          <article class="tarjeta" role="listitem">
            <h2 class="rotulo">Clientes activos</h2>
            <p class="cifra" [attr.aria-busy]="clientes() === null">{{ texto(clientes()) }}</p>
          </article>
        }
      </div>

      <nav class="rejilla" aria-label="Atajos">
        @if (puedeEmpleados) {
          <a class="tarjeta atajo" routerLink="/gestion/empleados">
            <span class="ficha" aria-hidden="true">E</span>
            <span>
              <strong>Empleados</strong>
              <span class="detalle">Crear, consultar, editar y dar de baja</span>
            </span>
            <span class="flecha" aria-hidden="true">→</span>
          </a>
        }
        @if (puedeDistribuidores) {
          <a class="tarjeta atajo" routerLink="/gestion/distribuidores">
            <span class="ficha" aria-hidden="true">D</span>
            <span>
              <strong>Distribuidores</strong>
              <span class="detalle">Crear, consultar, editar y dar de baja</span>
            </span>
            <span class="flecha" aria-hidden="true">→</span>
          </a>
        }
        @if (puedeClientes) {
          <a class="tarjeta atajo" routerLink="/gestion/clientes">
            <span class="ficha" aria-hidden="true">C</span>
            <span>
              <strong>Clientes</strong>
              <span class="detalle">Consulta básica y detallada</span>
            </span>
            <span class="flecha" aria-hidden="true">→</span>
          </a>
        }
      </nav>
    </section>
  `,
  styles: `
    .rejilla {
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
    .detalle {
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
    @media (max-width: 1100px) {
      .rejilla {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class InicioGestion implements OnInit {
  private readonly sesion = inject(SesionStore);
  private readonly empleadosApi = inject(EmpleadosApi);
  private readonly distribuidoresApi = inject(DistribuidoresApi);
  private readonly consultasApi = inject(ConsultasApi);

  protected readonly puedeEmpleados = this.sesion.tieneOperacion('GESTIONAR_EMPLEADOS');
  protected readonly puedeDistribuidores = this.sesion.tieneOperacion('GESTIONAR_DISTRIBUIDORES');
  protected readonly puedeClientes = this.sesion.tieneOperacion('CONSULTAR_REGISTROS');

  protected readonly empleados = signal<Conteo>(null);
  protected readonly distribuidores = signal<Conteo>(null);
  protected readonly clientes = signal<Conteo>(null);

  ngOnInit(): void {
    if (this.puedeEmpleados) void this.contar(this.empleadosApi.listar(), this.empleados);
    if (this.puedeDistribuidores) {
      void this.contar(this.distribuidoresApi.listar(), this.distribuidores);
    }
    if (this.puedeClientes) void this.contar(this.consultasApi.basico('CLIENTE'), this.clientes);
  }

  private async contar(
    consulta: ReturnType<EmpleadosApi['listar']>,
    destino: { set(v: Conteo): void },
  ): Promise<void> {
    try {
      const lista: ResumenDTO[] = await firstValueFrom(consulta);
      destino.set(lista.filter((r) => esActivo(r.estado)).length);
    } catch {
      destino.set('error');
    }
  }

  protected texto(c: Conteo): string {
    if (c === null) return '…';
    return c === 'error' ? '—' : c.toLocaleString('es-CO');
  }
}
