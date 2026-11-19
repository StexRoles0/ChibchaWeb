import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter, map } from 'rxjs';
import { SesionStore } from '../../core/auth/sesion.store';
import { DialogoConfirmacion } from '../../shared/dialogo-confirmacion';
import { vencimientoCorto } from '../../shared/formato';
import { PerfilStore } from './perfil.store';

const PLATAFORMAS: Record<string, string> = { UNIX: 'Unix', WINDOWS: 'Windows' };

/**
 * M-06 · Mi perfil (CU-CLI-01) y, sobre la misma pantalla, M-08 · Eliminar perfil (CU-CLI-02):
 * la ruta `/cliente/perfil/eliminar` abre el diálogo de confirmación.
 */
@Component({
  selector: 'app-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ReactiveFormsModule, DialogoConfirmacion],
  templateUrl: './perfil.html',
  styleUrl: './perfil.scss',
})
export class Perfil implements OnInit {
  protected readonly store = inject(PerfilStore);
  private readonly sesion = inject(SesionStore);
  private readonly router = inject(Router);

  protected readonly eliminando = toSignal(
    this.router.events.pipe(
      filter((e) => e instanceof NavigationEnd),
      map(() => this.router.url.split('?')[0].endsWith('/eliminar')),
    ),
    { initialValue: this.router.url.split('?')[0].endsWith('/eliminar') },
  );

  protected readonly correoConfirmacion = new FormControl('', { nonNullable: true });
  private readonly escrito = toSignal(this.correoConfirmacion.valueChanges, { initialValue: '' });
  protected readonly confirmado = computed(
    () =>
      this.escrito().trim().toLowerCase() ===
      (this.sesion.sesion()?.correo ?? '\u0000').toLowerCase(),
  );
  protected readonly ocupado = signal(false);
  protected readonly errorEliminar = signal<string | null>(null);

  protected readonly plataforma = (v: string) => PLATAFORMAS[v] ?? v;
  protected readonly vencimiento = vencimientoCorto;

  ngOnInit(): void {
    void this.store.cargar();
  }

  protected cancelarEliminar(): void {
    this.correoConfirmacion.reset('');
    this.errorEliminar.set(null);
    void this.router.navigateByUrl('/cliente/perfil');
  }

  protected async eliminar(): Promise<void> {
    if (!this.confirmado()) return;
    this.ocupado.set(true);
    this.errorEliminar.set(null);
    const error = await this.store.eliminar();
    this.ocupado.set(false);
    if (error) this.errorEliminar.set(error.mensaje);
  }
}
