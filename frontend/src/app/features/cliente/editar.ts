import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CategoriaPerfil } from '../../core/api/clientes.api';
import { ErrorApi } from '../../core/errores';
import { aPaquete, aPlan, Paquete, Plan } from '../../shared/catalogo';
import { campoDelError, ErroresCampo } from '../../shared/errores-formulario';
import { CamposPago } from '../../shared/formularios/campos-pago';
import { CamposPersonales } from '../../shared/formularios/campos-personales';
import { crearFormPago, leerPago } from '../../shared/formularios/pago';
import { crearFormPersonal, leerPersonal } from '../../shared/formularios/personal';
import { SelectorPaquetePlan } from '../../shared/selector-paquete-plan';
import { AccesoApi } from '../../core/api/acceso.api';
import { firstValueFrom } from 'rxjs';
import { PerfilStore } from './perfil.store';

interface Pestana {
  categoria: CategoriaPerfil;
  etiqueta: string;
}

export const PESTANAS: Pestana[] = [
  { categoria: 'PERSONAL', etiqueta: 'Información personal y sitio' },
  { categoria: 'PAQUETE_PLAN', etiqueta: 'Paquete y plan' },
  { categoria: 'PAGO', etiqueta: 'Dirección y tarjeta' },
];

/** El detalle trae el subdominio completo; el formulario edita solo el nombre corto. */
export const nombreCortoDeSitio = (sitio: string): string =>
  sitio.replace(/\.chibchaweb\.[a-z]+$/i, '');

/**
 * M-07 · Modificar perfil (CU-CLI-03). Tres pestañas (`?pestana=`), una por `CategoriaPerfil`;
 * *Guardar* manda solo el bloque de la pestaña activa con `PATCH /clientes/me?categoria=`.
 */
@Component({
  selector: 'app-editar-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ReactiveFormsModule, CamposPersonales, CamposPago, SelectorPaquetePlan],
  templateUrl: './editar.html',
  styleUrl: './editar.scss',
})
export class EditarPerfil implements OnInit {
  protected readonly store = inject(PerfilStore);
  private readonly accesoApi = inject(AccesoApi);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly pestanas = PESTANAS;
  private readonly params = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });
  protected readonly activa = computed<CategoriaPerfil>(() => {
    const p = this.params().get('pestana');
    return PESTANAS.find((t) => t.categoria === p)?.categoria ?? 'PERSONAL';
  });

  protected readonly formPersonal = crearFormPersonal();
  protected readonly formPago = crearFormPago();
  protected readonly erroresPersonal = new ErroresCampo([this.formPersonal]);
  protected readonly erroresPago = new ErroresCampo([this.formPago]);
  protected readonly idPaquete = signal<number | null>(null);
  protected readonly idPlan = signal<number | null>(null);
  protected readonly paquetes = signal<Paquete[]>([]);
  protected readonly planes = signal<Plan[]>([]);

  protected readonly guardando = signal(false);
  protected readonly exito = signal<string | null>(null);
  protected readonly errorGeneral = signal<string | null>(null);
  protected readonly listo = signal(false);

  async ngOnInit(): Promise<void> {
    await Promise.all([this.store.cargar(), this.cargarCatalogo()]);
    const p = this.store.perfil();
    if (!p) return;
    this.formPersonal.patchValue({
      nombre: p.nombre,
      telefono: p.telefono,
      lineaResidencia: p.lineaResidencia,
      ciudadResidencia: p.ciudadResidencia,
      codigoPostalResidencia: p.codigoPostalResidencia,
      sitio: nombreCortoDeSitio(p.sitio),
      plataforma: p.plataforma,
    });
    this.idPaquete.set(p.idPaquete);
    this.idPlan.set(p.idPlan);
    this.formPago.patchValue({
      lineaFacturacion: p.lineaFacturacion,
      ciudadFacturacion: p.ciudadFacturacion,
      codigoPostalFacturacion: p.codigoPostalFacturacion,
      franquicia: p.franquicia || 'VISA',
    });
    this.listo.set(true);
  }

  private async cargarCatalogo(): Promise<void> {
    try {
      const [paquetes, planes] = await Promise.all([
        firstValueFrom(this.accesoApi.paquetes()),
        firstValueFrom(this.accesoApi.planes()),
      ]);
      this.paquetes.set(paquetes.map(aPaquete));
      this.planes.set(planes.map(aPlan));
    } catch {
      // sin catálogo no se puede cambiar de plan; las otras pestañas siguen funcionando
    }
  }

  protected correo(): string {
    return this.store.perfil()?.correo ?? '';
  }

  protected cambiarPestana(categoria: CategoriaPerfil): void {
    this.exito.set(null);
    this.errorGeneral.set(null);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { pestana: categoria },
      replaceUrl: true,
    });
  }

  /** Flechas izquierda/derecha, Inicio y Fin entre pestañas. */
  protected teclado(ev: KeyboardEvent, indice: number): void {
    const n = PESTANAS.length;
    const destino =
      ev.key === 'ArrowRight'
        ? (indice + 1) % n
        : ev.key === 'ArrowLeft'
          ? (indice - 1 + n) % n
          : ev.key === 'Home'
            ? 0
            : ev.key === 'End'
              ? n - 1
              : -1;
    if (destino < 0) return;
    ev.preventDefault();
    this.cambiarPestana(PESTANAS[destino].categoria);
    document.getElementById(`pestana-${PESTANAS[destino].categoria}`)?.focus();
  }

  protected cancelar(): void {
    void this.router.navigateByUrl('/cliente/perfil');
  }

  protected async guardar(): Promise<void> {
    this.exito.set(null);
    this.errorGeneral.set(null);
    const categoria = this.activa();
    const cuerpo = this.armarCuerpo(categoria);
    if (!cuerpo) return;

    this.guardando.set(true);
    const error = await this.store.modificar(categoria, cuerpo);
    this.guardando.set(false);
    if (error) {
      this.mostrarError(categoria, error);
      return;
    }
    if (categoria === 'PAGO') {
      this.formPago.patchValue({ numeroTarjeta: '', vencimiento: '', codigoSeguridad: '' });
      this.formPago.controls.numeroTarjeta.markAsUntouched();
      this.formPago.controls.vencimiento.markAsUntouched();
      this.formPago.controls.codigoSeguridad.markAsUntouched();
    }
    this.exito.set(
      categoria === 'PAQUETE_PLAN'
        ? 'Listo: el nuevo paquete y plan se aplican desde tu próximo corte.'
        : 'Cambios guardados.',
    );
  }

  /** Solo el bloque de la pestaña activa; `null` si el formulario no es válido. */
  private armarCuerpo(categoria: CategoriaPerfil) {
    if (categoria === 'PERSONAL') {
      this.formPersonal.markAllAsTouched();
      return this.formPersonal.invalid ? null : leerPersonal(this.formPersonal, false);
    }
    if (categoria === 'PAGO') {
      this.formPago.markAllAsTouched();
      return this.formPago.invalid ? null : leerPago(this.formPago);
    }
    const idPaquete = this.idPaquete();
    const idPlan = this.idPlan();
    const idSuscripcion = this.store.perfil()?.idSuscripcion;
    if (idPaquete === null || idPlan === null || !idSuscripcion) {
      this.errorGeneral.set('Elige un paquete y un plan de pago.');
      return null;
    }
    return { idSuscripcion, idPaquete, idPlan };
  }

  private mostrarError(categoria: CategoriaPerfil, error: ErrorApi): void {
    const campo = campoDelError(error);
    const errores = categoria === 'PAGO' ? this.erroresPago : this.erroresPersonal;
    if (campo && categoria !== 'PAQUETE_PLAN') errores.fijar(campo, error.mensaje);
    // Contingencia: el banner global ya lo explica.
    if (error.codigo !== 'CONTINGENCIA') this.errorGeneral.set(error.mensaje);
  }
}
