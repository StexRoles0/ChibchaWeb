import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AccesoApi } from '../api/acceso.api';
import { ResultadoAccesoDTO } from '../api/dto';

@Injectable({ providedIn: 'root' })
export class SesionStore {
  private readonly api = inject(AccesoApi);
  private readonly router = inject(Router);

  private readonly _sesion = signal<ResultadoAccesoDTO | null>(null);
  private readonly _cargada = signal(false);

  readonly sesion = this._sesion.asReadonly();
  readonly cargada = this._cargada.asReadonly();
  /** Usuario ya registrado en el sistema. */
  readonly autenticada = computed(() => this._sesion()?.registrado === true);
  /** Identidad verificada por OAuth pero sin cuenta (debe registrarse). */
  readonly identidadPendiente = computed(() => {
    const s = this._sesion();
    return s !== null && !s.registrado;
  });
  readonly esCliente = computed(
    () => this.autenticada() && this._sesion()?.tipoUsuario === 'CLIENTE',
  );
  readonly operaciones = computed(() => this._sesion()?.operaciones ?? []);
  readonly nombre = computed(() => this._sesion()?.nombre ?? '');
  readonly rol = computed(() => this._sesion()?.rol);
  /** Ruta a la que se va después del login (docs/ui.md §Navegación). */
  readonly rutaInicio = computed(() => {
    const s = this._sesion();
    if (!s) return '/acceso';
    if (!s.registrado) return '/registro/datos';
    if (s.tipoUsuario === 'CLIENTE') return '/cliente';
    switch (s.rol) {
      case 'Gestión':
        return '/gestion';
      case 'Soporte':
        return '/soporte/bandeja';
      case 'Administrador':
        return '/admin';
      default:
        return '/acceso';
    }
  });

  tieneOperacion(operacion: string): boolean {
    return this.operaciones().includes(operacion);
  }

  establecer(sesion: ResultadoAccesoDTO | null): void {
    this._sesion.set(sesion);
    this._cargada.set(true);
  }

  /** GET /auth/sesion. Un error (401) deja la sesión vacía. */
  async cargar(): Promise<void> {
    try {
      this.establecer(await firstValueFrom(this.api.sesion()));
    } catch {
      this.establecer(null);
    }
  }

  async cerrarSesion(): Promise<void> {
    try {
      await firstValueFrom(this.api.logout());
    } catch {
      // aunque falle el servidor, se limpia la sesión local
    }
    this.establecer(null);
    await this.router.navigateByUrl('/acceso');
  }
}
