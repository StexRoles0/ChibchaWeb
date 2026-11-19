import { computed, Injectable, signal } from '@angular/core';

const TEXTO_RESPALDADA =
  'El sistema está en modo contingencia; tu operación quedó respaldada y se aplicará al restablecerse el servicio.';

/**
 * Estado del banner global de contingencia (503 CONTINGENCIA). Con la BD caída, solo las
 * operaciones que alcanzan a escribir quedan respaldadas; las demás (lecturas, escrituras que
 * fallan antes de escribir) no, así que el texto depende del mensaje del servidor.
 */
@Injectable({ providedIn: 'root' })
export class ContingenciaStore {
  private readonly _activa = signal(false);
  private readonly _mensaje = signal<string | null>(null);
  readonly activa = this._activa.asReadonly();

  /** Texto del banner. */
  readonly texto = computed(() => {
    const m = this._mensaje();
    if (!m || /respald/i.test(m)) return TEXTO_RESPALDADA;
    const llano = m.trim().replace(/[.\s]+$/, '');
    return `El sistema está en modo contingencia: ${llano.charAt(0).toLowerCase()}${llano.slice(1)}.`;
  });

  activar(mensaje?: string): void {
    this._mensaje.set(mensaje ?? null);
    this._activa.set(true);
  }

  descartar(): void {
    this._activa.set(false);
  }
}
