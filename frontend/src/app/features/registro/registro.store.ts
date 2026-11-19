import { computed, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AccesoApi } from '../../core/api/acceso.api';
import { DatosClienteDTO } from '../../core/api/dto';
import { SesionStore } from '../../core/auth/sesion.store';
import { ErrorApi } from '../../core/errores';
import { aPaquete, aPlan, Paquete, Plan } from '../../shared/catalogo';
import { BloquePago } from '../../shared/formularios/pago';
import { leerPersonal } from '../../shared/formularios/personal';
import { campoDelError } from '../../shared/errores-formulario';

export type PasoRegistro = 'datos' | 'plan' | 'pago';

export type DatosPersonales = ReturnType<typeof leerPersonal>;
/** El código de seguridad no se conserva: se vuelve a pedir en M-04. */
export type PagoGuardado = Omit<BloquePago, 'codigoSeguridad'>;

const CAMPOS_PLAN = ['idPaquete', 'idPlan'];
const CAMPOS_DATOS = [
  'nombre',
  'telefono',
  'lineaResidencia',
  'ciudadResidencia',
  'codigoPostalResidencia',
  'sitio',
  'plataforma',
  'codigoDistribuidor',
];

/** Paso del asistente donde está un campo del contrato. */
export function pasoDeCampo(campo: string | undefined): PasoRegistro {
  if (campo && CAMPOS_DATOS.includes(campo)) return 'datos';
  if (campo && CAMPOS_PLAN.includes(campo)) return 'plan';
  return 'pago';
}

export interface ErrorPendiente {
  paso: PasoRegistro;
  campo?: string;
  mensaje: string;
}

/**
 * Datos del asistente M-02 → M-04 hasta *Crear cuenta*. Se provee en la ruta `/registro`:
 * al salir del registro (o cancelarlo) el estado desaparece.
 */
@Injectable()
export class RegistroStore {
  private readonly api = inject(AccesoApi);
  private readonly sesion = inject(SesionStore);

  readonly paquetes = signal<Paquete[]>([]);
  readonly planes = signal<Plan[]>([]);
  readonly catalogoCargado = signal(false);
  readonly errorCatalogo = signal<string | null>(null);

  readonly datos = signal<DatosPersonales | null>(null);
  readonly plan = signal<{ idPaquete: number; idPlan: number } | null>(null);
  readonly pago = signal<PagoGuardado | null>(null);

  readonly enviando = signal(false);
  /** Error del servidor que hay que mostrar en el paso `paso` (lo toma el componente de ese paso). */
  readonly errorPendiente = signal<ErrorPendiente | null>(null);
  /** Error general del envío (sin campo): aviso arriba del formulario de M-04. */
  readonly errorGeneral = signal<string | null>(null);

  readonly datosCompletos = computed(() => this.datos() !== null);
  readonly planCompleto = computed(() => this.datosCompletos() && this.plan() !== null);

  async cargarCatalogo(): Promise<void> {
    if (this.catalogoCargado()) return;
    try {
      const [paquetes, planes] = await Promise.all([
        firstValueFrom(this.api.paquetes()),
        firstValueFrom(this.api.planes()),
      ]);
      this.paquetes.set(paquetes.map(aPaquete));
      this.planes.set(planes.map(aPlan));
      this.catalogoCargado.set(true);
      this.errorCatalogo.set(null);
    } catch (e) {
      this.errorCatalogo.set((e as ErrorApi).mensaje ?? 'No se pudo cargar el catálogo.');
    }
  }

  guardarDatos(datos: DatosPersonales): void {
    this.datos.set(datos);
  }

  guardarPlan(idPaquete: number, idPlan: number): void {
    this.plan.set({ idPaquete, idPlan });
  }

  /** Quita y entrega el error pendiente si es del paso indicado. */
  tomarError(paso: PasoRegistro): ErrorPendiente | null {
    const e = this.errorPendiente();
    if (e?.paso !== paso) return null;
    this.errorPendiente.set(null);
    return e;
  }

  /** Arma el cuerpo de `POST /auth/registro` (el correo no va: sale de la identidad pendiente). */
  armarDto(pago: BloquePago): DatosClienteDTO | null {
    const datos = this.datos();
    const plan = this.plan();
    if (!datos || !plan) return null;
    const dto: DatosClienteDTO = {
      ...datos,
      idPaquete: plan.idPaquete,
      idPlan: plan.idPlan,
      ...pago,
    };
    if (!dto.codigoDistribuidor) delete dto.codigoDistribuidor;
    return dto;
  }

  /**
   * `POST /auth/registro`. Devuelve el paso al que hay que volver si el servidor rechazó un
   * campo de otro paso; `null` si salió bien (la sesión queda abierta) o si el error se muestra
   * en el paso actual.
   */
  async crear(pago: BloquePago): Promise<'ok' | PasoRegistro> {
    const dto = this.armarDto(pago);
    if (!dto) return 'datos';
    const { codigoSeguridad: _cvv, ...guardado } = pago;
    void _cvv;
    this.pago.set(guardado);
    this.enviando.set(true);
    this.errorGeneral.set(null);
    this.errorPendiente.set(null);
    try {
      const resultado = await firstValueFrom(this.api.registro(dto));
      this.sesion.establecer(resultado);
      return 'ok';
    } catch (e) {
      const err = e as ErrorApi;
      const campo = campoDelError(err);
      const paso = campo ? pasoDeCampo(campo) : 'pago';
      if (err.codigo === 'CONTINGENCIA') {
        // El banner global ya avisa; no hay campo que marcar.
        return 'pago';
      }
      if (campo) this.errorPendiente.set({ paso, campo, mensaje: err.mensaje });
      else this.errorGeneral.set(err.mensaje);
      return paso;
    } finally {
      this.enviando.set(false);
    }
  }

  /** *Cancelar registro* → `POST /auth/logout` → M-01. */
  cancelar(): Promise<void> {
    return this.sesion.cerrarSesion();
  }
}
