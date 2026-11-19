import { Injectable } from '@angular/core';

/** Redirección completa del navegador (hacia el proveedor OAuth). Aislada para poder simularla en pruebas. */
@Injectable({ providedIn: 'root' })
export class Navegador {
  ir(url: string): void {
    window.location.assign(url);
  }
}
