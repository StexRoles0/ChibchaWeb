import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

const COLORES: Record<string, 'azul' | 'oro' | 'verde' | 'rojo' | 'gris'> = {
  ABIERTO: 'azul',
  REGISTRADA: 'azul',
  ESCALADO: 'oro',
  SIMULADA: 'oro',
  RESUELTO: 'verde',
  ENVIADA: 'verde',
  EJECUTADA: 'verde',
  EXITOSO: 'verde',
  ACTIVO: 'verde',
  FALLIDA: 'rojo',
  REVERTIDA: 'rojo',
  FALLIDO: 'rojo',
  CANCELADA: 'rojo',
  INACTIVO: 'gris',
};

/** Etiqueta de estado: el texto siempre acompaña al color. */
@Component({
  selector: 'app-etiqueta-estado',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="etiqueta" [class]="color()">{{ texto() }}</span>`,
})
export class EtiquetaEstado {
  readonly estado = input.required<string>();
  /** Texto a mostrar; por defecto, el estado con la primera letra en mayúscula. */
  readonly etiqueta = input<string>();

  protected readonly color = computed(() => COLORES[this.estado().toUpperCase()] ?? 'azul');
  protected readonly texto = computed(() => {
    const t = this.etiqueta();
    if (t) return t;
    const e = this.estado().toLowerCase();
    return e.charAt(0).toUpperCase() + e.slice(1);
  });
}
