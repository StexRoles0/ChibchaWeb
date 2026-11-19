import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  contentChild,
  Directive,
  input,
  TemplateRef,
} from '@angular/core';

export interface ColumnaTabla {
  /** Propiedad de la fila que se muestra por defecto. */
  clave: string;
  titulo: string;
  /** Si es true, el encabezado solo se lee con lector de pantalla (p. ej. la columna de acciones). */
  ocultarTitulo?: boolean;
}

export interface ContextoCelda<T> {
  $implicit: T;
  columna: ColumnaTabla;
}

/** Plantilla de celda: `<ng-template appCelda let-fila let-columna="columna">…</ng-template>`. */
@Directive({ selector: 'ng-template[appCelda]' })
export class CeldaTabla {}

/**
 * Tabla accesible con encabezados `th scope="col"`, estado vacío y celdas personalizables.
 * Sin plantilla de celda, cada celda muestra `fila[columna.clave]`.
 */
@Component({
  selector: 'app-tabla',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NgTemplateOutlet],
  template: `
    <div class="envoltura">
      <table>
        <caption class="solo-lector">
          {{
            descripcion()
          }}
        </caption>
        <thead>
          <tr>
            @for (c of columnas(); track c.clave) {
              <th scope="col">
                @if (c.ocultarTitulo) {
                  <span class="solo-lector">{{ c.titulo }}</span>
                } @else {
                  {{ c.titulo }}
                }
              </th>
            }
          </tr>
        </thead>
        <tbody>
          @for (fila of filas(); track $index) {
            <tr>
              @for (c of columnas(); track c.clave) {
                <td>
                  @if (plantilla(); as t) {
                    <ng-container
                      [ngTemplateOutlet]="t"
                      [ngTemplateOutletContext]="{ $implicit: fila, columna: c }"
                    />
                  } @else {
                    {{ valor(fila, c) }}
                  }
                </td>
              }
            </tr>
          } @empty {
            <tr>
              <td class="vacio" [attr.colspan]="columnas().length">{{ textoVacio() }}</td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: `
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
      border-top: 1px solid var(--linea);
      border-bottom: 1px solid var(--linea);
    }
    td {
      padding: 16px 20px;
      vertical-align: middle;
      border-bottom: 1px solid var(--linea);
    }
    tbody tr:last-child td {
      border-bottom: 0;
    }
    .vacio {
      padding: 36px 20px;
      text-align: center;
      color: var(--tinta-2);
    }
  `,
})
export class Tabla<T extends object> {
  readonly columnas = input.required<ColumnaTabla[]>();
  readonly filas = input.required<T[]>();
  /** Título de la tabla para lectores de pantalla. */
  readonly descripcion = input('Tabla de resultados');
  readonly textoVacio = input('No hay registros para mostrar.');

  protected readonly plantilla = contentChild(CeldaTabla, { read: TemplateRef });

  protected valor(fila: T, c: ColumnaTabla): string {
    const v = (fila as Record<string, unknown>)[c.clave];
    return v === undefined || v === null ? '' : String(v);
  }
}
