import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AccesoApi } from '../../core/api/acceso.api';
import { SesionStore } from '../../core/auth/sesion.store';
import { ErrorApi } from '../../core/errores';

/**
 * `/auth/callback` · CU-AUTH-02. Manda `code` y `state` a `POST /auth/oauth/callback` y redirige
 * según el rol (o a M-02 si falta registrarse). Si falla, vuelve a M-01 con el mensaje.
 */
@Component({
  selector: 'app-callback',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="centro" role="status" aria-live="polite">
      <p>Procesando acceso…</p>
    </main>
  `,
  styles: `
    .centro {
      display: grid;
      place-items: center;
      min-height: 100vh;
      font-size: 16px;
      color: var(--tinta-2);
    }
  `,
})
export class Callback implements OnInit {
  private readonly ruta = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(AccesoApi);
  private readonly sesion = inject(SesionStore);

  async ngOnInit(): Promise<void> {
    const q = this.ruta.snapshot.queryParamMap;
    const codigo = q.get('code');
    const estado = q.get('state');
    if (!codigo || !estado) {
      await this.fallar('El proveedor no devolvió los datos del acceso. Inténtalo de nuevo.');
      return;
    }
    try {
      const resultado = await firstValueFrom(this.api.callback({ codigo, estado }));
      this.sesion.establecer(resultado);
      await this.router.navigateByUrl(this.sesion.rutaInicio(), { replaceUrl: true });
    } catch (e) {
      const err = e as ErrorApi;
      await this.fallar(err.mensaje ?? 'No se pudo completar el acceso.');
    }
  }

  private async fallar(mensaje: string): Promise<void> {
    this.sesion.establecer(null);
    await this.router.navigateByUrl('/acceso', { replaceUrl: true, state: { error: mensaje } });
  }
}
