import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AccesoApi } from '../../core/api/acceso.api';
import { ErrorApi } from '../../core/errores';
import { Navegador } from '../../core/navegador';
import { Marca } from '../../shared/marca';

/**
 * M-01 · Acceso (CU-AUTH-01). Los dos botones piden `GET /auth/oauth/inicio` y redirigen al
 * proveedor; crear cuenta también exige autenticarse primero. En desarrollo hay un campo
 * "correo de prueba" que manda el código `dev:<correo>`.
 */
@Component({
  selector: 'app-acceso',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, Marca],
  templateUrl: './acceso.html',
  styleUrl: './acceso.scss',
})
export class Acceso {
  private readonly api = inject(AccesoApi);
  private readonly navegador = inject(Navegador);
  private readonly router = inject(Router);

  /** Solo fuera de producción. */
  protected readonly modoPrueba = !environment.production;
  protected readonly correosPrueba = [
    'steven@correo.co',
    'gestion@chibchaweb.co',
    'soporte@chibchaweb.co',
    'admin@chibchaweb.co',
    'nuevo.usuario@correo.co',
  ];
  protected readonly correo = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.email],
  });

  protected readonly ocupado = signal(false);
  /** Error de un intento anterior (p. ej. el callback fallido) o de este intento. */
  protected readonly error = signal<string | null>(
    ((this.router.currentNavigation()?.extras.state ?? history.state) as { error?: string } | null)
      ?.error ?? null,
  );
  protected readonly intentoSinCorreo = signal(false);

  protected async iniciar(): Promise<void> {
    this.error.set(null);
    if (this.modoPrueba && this.correo.invalid) {
      this.correo.markAsTouched();
      this.intentoSinCorreo.set(true);
      return;
    }
    this.ocupado.set(true);
    try {
      const { url } = await firstValueFrom(
        this.api.oauthInicio(this.modoPrueba ? this.correo.value.trim() : undefined),
      );
      this.navegador.ir(url);
    } catch (e) {
      this.error.set((e as ErrorApi).mensaje ?? 'No se pudo iniciar el acceso.');
      this.ocupado.set(false);
    }
  }
}
