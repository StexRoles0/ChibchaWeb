import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { SesionStore } from '../core/auth/sesion.store';
import { etiquetaRol, iniciales, ItemMenu, menuPara } from './menu';

@Component({
  selector: 'app-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  private readonly sesion = inject(SesionStore);

  protected readonly menuAbierto = signal(false);
  protected readonly nombre = this.sesion.nombre;
  protected readonly iniciales = computed(() => iniciales(this.nombre()));
  protected readonly etiquetaRol = computed(() =>
    etiquetaRol(this.sesion.sesion()?.tipoUsuario ?? '', this.sesion.rol()),
  );
  protected readonly items = computed<ItemMenu[]>(() =>
    menuPara(this.sesion.sesion()?.tipoUsuario ?? '', this.sesion.rol()).filter(
      (i) => !i.operacion || this.sesion.tieneOperacion(i.operacion),
    ),
  );

  protected alternarMenu(): void {
    this.menuAbierto.update((v) => !v);
  }

  protected cerrarMenu(): void {
    this.menuAbierto.set(false);
  }

  protected cerrarSesion(): void {
    void this.sesion.cerrarSesion();
  }
}
