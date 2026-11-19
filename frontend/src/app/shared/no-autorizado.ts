import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-no-autorizado',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="pagina">
      <div>
        <h1>No tienes permiso</h1>
        <p class="subtitulo">Tu rol no permite entrar a esta página.</p>
      </div>
      <p><a class="boton" routerLink="/">Volver al inicio</a></p>
    </section>
  `,
})
export class NoAutorizado {}
