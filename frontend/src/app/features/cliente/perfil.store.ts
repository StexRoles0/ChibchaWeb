import { inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { CategoriaPerfil, ClientesApi } from '../../core/api/clientes.api';
import { DatosClienteDTO } from '../../core/api/dto';
import { SesionStore } from '../../core/auth/sesion.store';
import { ErrorApi } from '../../core/errores';
import { camposDeDetalle } from '../../shared/formato';

/** `DetalleDTO` de CLIENTE con sus claves fijas (api.md), ya con tipos. */
export interface PerfilCliente {
  nombre: string;
  correo: string;
  telefono: string;
  lineaResidencia: string;
  ciudadResidencia: string;
  codigoPostalResidencia: string;
  lineaFacturacion: string;
  ciudadFacturacion: string;
  codigoPostalFacturacion: string;
  tarjeta: string;
  franquicia: string;
  vencimiento: string;
  idSuscripcion: number;
  sitio: string;
  plataforma: string;
  idPaquete: number;
  paquete: string;
  idPlan: number;
  plan: string;
  montoPeriodo: string;
  fechaCorte: string;
  distribuidor: string;
  activo: boolean;
}

export function aPerfil(campos: Record<string, string>): PerfilCliente {
  const t = (k: string) => campos[k] ?? '';
  return {
    nombre: t('nombre'),
    correo: t('correo'),
    telefono: t('telefono'),
    lineaResidencia: t('lineaResidencia'),
    ciudadResidencia: t('ciudadResidencia'),
    codigoPostalResidencia: t('codigoPostalResidencia'),
    lineaFacturacion: t('lineaFacturacion'),
    ciudadFacturacion: t('ciudadFacturacion'),
    codigoPostalFacturacion: t('codigoPostalFacturacion'),
    tarjeta: t('tarjeta'),
    franquicia: t('franquicia'),
    vencimiento: t('vencimiento'),
    idSuscripcion: Number(t('idSuscripcion')),
    sitio: t('sitio'),
    plataforma: t('plataforma'),
    idPaquete: Number(t('idPaquete')),
    paquete: t('paquete'),
    idPlan: Number(t('idPlan')),
    plan: t('plan'),
    montoPeriodo: t('montoPeriodo'),
    fechaCorte: t('fechaCorte'),
    distribuidor: t('distribuidor'),
    activo: t('activo').toLowerCase() === 'true',
  };
}

/** Perfil del cliente en sesión para M-05 a M-08. Se provee en las rutas de `/cliente`. */
@Injectable()
export class PerfilStore {
  private readonly api = inject(ClientesApi);
  private readonly sesion = inject(SesionStore);
  private readonly router = inject(Router);

  readonly perfil = signal<PerfilCliente | null>(null);
  readonly cargando = signal(false);
  readonly error = signal<string | null>(null);

  /** `GET /clientes/me` */
  async cargar(): Promise<void> {
    this.cargando.set(true);
    this.error.set(null);
    try {
      this.perfil.set(aPerfil(camposDeDetalle(await firstValueFrom(this.api.detalle()))));
    } catch (e) {
      this.error.set((e as ErrorApi).mensaje ?? 'No se pudo cargar tu perfil.');
    } finally {
      this.cargando.set(false);
    }
  }

  /** `PATCH /clientes/me?categoria=`; devuelve el error del servidor si lo hay. */
  async modificar(
    categoria: CategoriaPerfil,
    datos: Partial<DatosClienteDTO>,
  ): Promise<ErrorApi | null> {
    try {
      await firstValueFrom(this.api.modificar(categoria, datos));
    } catch (e) {
      return e as ErrorApi;
    }
    await this.cargar();
    // El nombre del encabezado sale de la sesión.
    if (categoria === 'PERSONAL') await this.sesion.cargar();
    return null;
  }

  /** `DELETE /clientes/me`: la sesión se cierra y se va a M-01. */
  async eliminar(): Promise<ErrorApi | null> {
    try {
      await firstValueFrom(this.api.eliminar());
    } catch (e) {
      return e as ErrorApi;
    }
    this.sesion.establecer(null);
    this.perfil.set(null);
    await this.router.navigateByUrl('/acceso');
    return null;
  }
}
