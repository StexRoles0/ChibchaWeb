import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { CeldaTabla, ColumnaTabla, Tabla } from './tabla';

@Component({
  imports: [Tabla, CeldaTabla],
  template: `
    <app-tabla [columnas]="columnas" [filas]="filas" descripcion="Prueba" textoVacio="Nada aquí">
      @if (conPlantilla) {
        <ng-template appCelda let-fila let-columna="columna">
          <b>{{ columna.clave }}={{ fila[columna.clave] }}</b>
        </ng-template>
      }
    </app-tabla>
  `,
})
class Anfitrion {
  columnas: ColumnaTabla[] = [
    { clave: 'a', titulo: 'Columna A' },
    { clave: 'b', titulo: 'Acciones', ocultarTitulo: true },
  ];
  filas: object[] = [
    { a: 'uno', b: 'x' },
    { a: 'dos', b: 'y' },
  ];
  conPlantilla = false;
}

describe('Tabla', () => {
  async function montar(cambios: Partial<Anfitrion> = {}) {
    const f = TestBed.createComponent(Anfitrion);
    Object.assign(f.componentInstance, cambios);
    await f.whenStable();
    return f.nativeElement as HTMLElement;
  }

  it('encabezados con scope="col", caption y valores por defecto', async () => {
    const el = await montar();
    const ths = Array.from(el.querySelectorAll('th'));
    expect(ths.map((t) => t.getAttribute('scope'))).toEqual(['col', 'col']);
    expect(el.querySelector('caption')?.textContent).toContain('Prueba');
    expect(el.querySelectorAll('tbody tr').length).toBe(2);
    expect(el.querySelector('tbody td')?.textContent?.trim()).toBe('uno');
  });

  it('el título oculto sigue disponible para lectores de pantalla', async () => {
    const el = await montar();
    expect(el.querySelectorAll('th')[1].querySelector('.solo-lector')?.textContent).toContain(
      'Acciones',
    );
  });

  it('usa la plantilla de celda cuando existe', async () => {
    const el = await montar({ conPlantilla: true });
    expect(el.querySelector('tbody td b')?.textContent).toBe('a=uno');
  });

  it('sin filas muestra el texto de vacío ocupando todas las columnas', async () => {
    const el = await montar({ filas: [] });
    const td = el.querySelector('td.vacio')!;
    expect(td.textContent).toContain('Nada aquí');
    expect(td.getAttribute('colspan')).toBe('2');
  });
});
