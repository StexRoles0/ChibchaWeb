import { computed, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { EstadoMigracion, MigracionApi } from '../../core/api/migracion.api';
import { ErrorApi } from '../../core/errores';

export interface EntradaLog {
  /** `INFO` o `ERROR` (el backend no emite otros niveles). */
  nivel: string;
  tipo: string;
  idLegado: string;
  mensaje: string;
}

export interface Proceso {
  id: number;
  /** `SIMULADA` hasta confirmar o cancelar (RN-25). */
  estado: 'SIMULADA' | EstadoMigracion;
  validos: number;
  invalidos: number;
  entradas: EntradaLog[];
}

export interface ResumenTipo {
  tipo: string;
  titulo: string;
  validos: number;
  leidos: number;
}

const TIPOS: { tipo: string; titulo: string }[] = [
  { tipo: 'CLIENTE', titulo: 'Clientes' },
  { tipo: 'HOSTING', titulo: 'Registros de hosting' },
  { tipo: 'PAGO', titulo: 'Historial de pagos' },
];

/** `"NIVEL|tipo|idLegado|mensaje"` → entrada del log (el mensaje puede contener `|`). */
export function aEntrada(texto: string): EntradaLog {
  const [nivel = '', tipo = '', idLegado = '', ...resto] = texto.split('|');
  return {
    nivel: nivel.toUpperCase(),
    tipo: tipo.toUpperCase(),
    idLegado,
    mensaje: resto.join('|'),
  };
}

/**
 * Estado de la migración en curso (CU-MIG-01). Vive mientras dure el área de administración:
 * el contrato no tiene un `GET` del proceso, así que solo se conoce el que se simuló aquí.
 */
@Injectable()
export class MigracionStore {
  private readonly api = inject(MigracionApi);

  private readonly _proceso = signal<Proceso | null>(null);
  readonly proceso = this._proceso.asReadonly();
  readonly ocupado = signal<'simulando' | 'confirmando' | 'cancelando' | null>(null);
  readonly error = signal<string | null>(null);
  /** Resultado de la última confirmación o cancelación, para mostrarlo. */
  readonly resultado = signal<EstadoMigracion | null>(null);

  /** Cada tarjeta se deriva del log: una entrada por registro leído (RN-26). */
  readonly resumen = computed<ResumenTipo[]>(() => {
    const p = this._proceso();
    if (!p) return [];
    return TIPOS.map(({ tipo, titulo }) => {
      const propias = p.entradas.filter((e) => e.tipo === tipo);
      return {
        tipo,
        titulo,
        leidos: propias.length,
        validos: propias.filter((e) => e.nivel !== 'ERROR').length,
      };
    });
  });

  /** *Ejecutar migración real* solo se habilita con un proceso `SIMULADA`. */
  readonly puedeEjecutar = computed(
    () => this._proceso()?.estado === 'SIMULADA' && this.ocupado() === null,
  );

  async simular(): Promise<void> {
    this.ocupado.set('simulando');
    this.error.set(null);
    this.resultado.set(null);
    try {
      const r = await firstValueFrom(this.api.simular());
      this._proceso.set({
        id: r.idProceso,
        estado: 'SIMULADA',
        validos: r.validos,
        invalidos: r.invalidos,
        entradas: r.entradas.map(aEntrada),
      });
    } catch (e) {
      this.error.set((e as ErrorApi).mensaje);
    } finally {
      this.ocupado.set(null);
    }
  }

  async confirmar(): Promise<void> {
    await this.cambiar('confirmando', (id) => this.api.confirmar(id));
  }

  async cancelar(): Promise<void> {
    await this.cambiar('cancelando', (id) => this.api.cancelar(id));
  }

  private async cambiar(
    estado: 'confirmando' | 'cancelando',
    llamar: (id: number) => ReturnType<MigracionApi['confirmar']>,
  ): Promise<void> {
    const p = this._proceso();
    if (!p) return;
    this.ocupado.set(estado);
    this.error.set(null);
    try {
      const r = await firstValueFrom(llamar(p.id));
      this._proceso.set({ ...p, estado: r.estado });
      this.resultado.set(r.estado);
    } catch (e) {
      // 409 ESTADO_INVALIDO, 404, 422: se muestra el mensaje y el proceso no cambia.
      this.error.set((e as ErrorApi).mensaje);
    } finally {
      this.ocupado.set(null);
    }
  }
}
