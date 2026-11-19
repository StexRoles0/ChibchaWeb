/** Almacén del modo simulado: localStorage si existe, memoria si no (pruebas, ventanas privadas). */
const memoria = new Map<string, string>();
const PREFIJO = 'chibchaweb.simulado.';

export function leer<T>(clave: string, defecto: T): T {
  let crudo: string | null | undefined;
  try {
    crudo = localStorage.getItem(PREFIJO + clave);
  } catch {
    crudo = memoria.get(clave);
  }
  if (crudo === null || crudo === undefined) return defecto;
  try {
    return JSON.parse(crudo) as T;
  } catch {
    return defecto;
  }
}

export function guardar(clave: string, valor: unknown): void {
  const crudo = JSON.stringify(valor);
  try {
    localStorage.setItem(PREFIJO + clave, crudo);
  } catch {
    memoria.set(clave, crudo);
  }
}

export function borrar(clave: string): void {
  try {
    localStorage.removeItem(PREFIJO + clave);
  } catch {
    memoria.delete(clave);
  }
}

/** Para las pruebas: deja el modo simulado como recién abierto. */
export function reiniciarSimulado(): void {
  memoria.clear();
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith(PREFIJO))
      .forEach((k) => localStorage.removeItem(k));
  } catch {
    // sin almacenamiento
  }
}
