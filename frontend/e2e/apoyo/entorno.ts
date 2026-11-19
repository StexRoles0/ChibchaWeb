import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';

/**
 * Acceso al entorno e2e (docker-compose.e2e.yml, proyecto chibchaweb_e2e): comandos del backend
 * (CU sin pantalla), SQL de solo lectura para comprobar la persistencia y control del contenedor `db`.
 */
export const RAIZ = path.resolve(__dirname, '../../..');
const COMPOSE = ['compose', '-f', path.join(RAIZ, 'docker-compose.e2e.yml')];

export function compose(args: string[], entrada?: string): string {
  return execFileSync('docker', [...COMPOSE, ...args], {
    cwd: RAIZ,
    encoding: 'utf8',
    input: entrada,
    stdio: [entrada === undefined ? 'ignore' : 'pipe', 'pipe', 'pipe'],
  });
}

/**
 * Deja un evento real en el respaldo de contingencia (la BD "cae" justo al escribir una solicitud de dominio del
 * cliente `idCliente`, con el algoritmo indicado). Ver `evento_respaldado.py`.
 */
export function respaldarSolicitudDominio(idCliente: number, nombre: string, algoritmo: string): void {
  const salida = compose(
    ['exec', '-T', '-e', `E2E_CLIENTE=${idCliente}`, '-e', `E2E_NOMBRE=${nombre}`, '-e', `E2E_ALGORITMO=${algoritmo}`, 'backend', 'python', 'manage.py', 'shell'],
    readFileSync(path.join(__dirname, 'evento_respaldado.py'), 'utf8'),
  );
  if (!salida.includes('RESPALDADO')) throw new Error(`No se pudo respaldar el evento: ${salida}`);
}

/** `docker compose exec backend python manage.py <args>`; devuelve la salida estándar. */
export function manage(...args: string[]): string {
  return compose(['exec', '-T', 'backend', 'python', 'manage.py', ...args]);
}

/** Consulta de solo lectura a la BD e2e. Filas separadas por salto de línea y columnas por `|`. */
export function sql(consulta: string): string {
  return compose(['exec', '-T', 'db', 'psql', '-U', 'chibcha', '-d', 'chibchaweb', '-At', '-F', '|', '-c', consulta]).trim();
}

/** Fecha de hoy en Bogotá (la zona del backend), AAAA-MM-DD. */
export function hoyBogota(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(new Date());
}

/** Suma meses con el recorte de fin de mes que usa el backend (31 ene + 1 mes = 28/29 feb). */
export function sumarMeses(fecha: string, meses: number): string {
  const [a, m, d] = fecha.split('-').map(Number);
  const total = a * 12 + (m - 1) + meses;
  const anio = Math.floor(total / 12);
  const mes = (total % 12) + 1;
  const ultimo = new Date(Date.UTC(anio, mes, 0)).getUTCDate();
  return `${anio}-${String(mes).padStart(2, '0')}-${String(Math.min(d, ultimo)).padStart(2, '0')}`;
}

const arranque = Date.now().toString(36);
let contador = 0;
/** Sufijo único por corrida y por llamada (minúsculas y dígitos), para correos, sitios y documentos. */
export function unico(): string {
  contador += 1;
  return `${arranque}${contador}`;
}

export function dbDetener(): void {
  compose(['stop', 'db']);
}

export function dbIniciar(): void {
  compose(['start', 'db']);
  // `--wait` en `up` no existe en `start`: se espera al healthcheck con `up -d --wait db`.
  compose(['up', '-d', '--wait', 'db']);
}

/** AAAA-MM-DD como la muestra la interfaz ("17 nov 2026"). */
export function fechaCortaUi(iso: string): string {
  const meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
  const [a, m, d] = iso.split('-').map(Number);
  return `${d} ${meses[m - 1]} ${a}`;
}
