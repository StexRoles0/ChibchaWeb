import { expect, Page } from '@playwright/test';
import { unico } from './entorno';

export const GESTION = 'gestion@chibchaweb.co';
export const SOPORTE = 'soporte@chibchaweb.co';
export const ADMIN = 'admin@chibchaweb.co';

export const VISA_VALIDA = '4242424242424242';
export const VISA_RECHAZADA_VALIDADOR = '4000000000000002';
export const VISA_COBRO_FALLIDO = '4000000000000341';

/** Escribe el correo de prueba en M-01 y pulsa *Iniciar sesión*; el proveedor simulado devuelve `dev:<correo>`. */
export async function ingresar(page: Page, correo: string, boton: RegExp = /Iniciar sesión con proveedor/): Promise<void> {
  await page.goto('/acceso');
  await page.getByLabel(/Correo de prueba/).fill(correo);
  await page.getByRole('button', { name: boton }).click();
}

/** Ingresa y espera a llegar a la ruta de inicio del rol. */
export async function ingresarComo(page: Page, correo: string, ruta: RegExp): Promise<void> {
  await ingresar(page, correo);
  await expect(page).toHaveURL(ruta);
}

export async function cerrarSesion(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL(/\/acceso$/);
}

export interface DatosRegistro {
  correo: string;
  nombre: string;
  sitio: string;
  telefono: string;
  paquete: string;
  plan: string;
  tarjeta: string;
  codigoDistribuidor?: string;
}

export function datosRegistro(parcial: Partial<DatosRegistro> = {}): DatosRegistro {
  const u = unico();
  return {
    correo: `cliente${u}@correo.co`,
    nombre: `Cliente Prueba ${u}`,
    sitio: `sitio${u}`,
    telefono: '3001234567',
    paquete: 'Chibcha-Oro',
    plan: 'Semestral',
    tarjeta: VISA_VALIDA,
    ...parcial,
  };
}

/** M-02: completa los datos del paso 1 (el nombre ya llega lleno) y pulsa *Continuar*. */
export async function llenarPaso1(page: Page, d: DatosRegistro): Promise<void> {
  await page.getByLabel('Nombre completo').fill(d.nombre);
  await page.getByLabel('Teléfono').fill(d.telefono);
  await page.getByLabel('Dirección de residencia').fill('Calle 10 # 5-20');
  await page.getByLabel('Ciudad de residencia').fill('Sogamoso');
  await page.getByLabel('Código postal').fill('152210');
  await page.getByLabel('Sitio web a hospedar').fill(d.sitio);
  await page.getByLabel('Plataforma').selectOption({ index: 1 });
  if (d.codigoDistribuidor) await page.getByLabel(/Código de distribuidor/).fill(d.codigoDistribuidor);
  await page.getByRole('button', { name: 'Continuar' }).click();
}

/** M-03: elige paquete y plan y pulsa *Continuar*. */
export async function llenarPaso2(page: Page, d: DatosRegistro): Promise<void> {
  await expect(page).toHaveURL(/\/registro\/plan$/);
  await page.getByRole('radio', { name: new RegExp(d.paquete) }).check({ force: true });
  await page.getByRole('radio', { name: new RegExp(d.plan) }).check({ force: true });
  await page.getByRole('button', { name: 'Continuar' }).click();
}

/** M-04: dirección de facturación, tarjeta y *Crear cuenta*. */
export async function llenarPaso3(page: Page, d: DatosRegistro): Promise<void> {
  await expect(page).toHaveURL(/\/registro\/pago$/);
  await page.getByLabel('Número de tarjeta').fill(d.tarjeta);
  await page.getByLabel('Vencimiento').fill('12/30');
  await page.getByLabel('Código de seguridad').fill('123');
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
}

/** Registro completo de un cliente nuevo por la interfaz (AUTH-03); termina en M-05. */
export async function registrarCliente(page: Page, parcial: Partial<DatosRegistro> = {}): Promise<DatosRegistro> {
  const d = datosRegistro(parcial);
  await ingresar(page, d.correo);
  await expect(page).toHaveURL(/\/registro\/datos$/);
  await llenarPaso1(page, d);
  await llenarPaso2(page, d);
  await llenarPaso3(page, d);
  await expect(page).toHaveURL(/\/cliente$/);
  return d;
}

/** Texto del contenido principal (sin el menú ni la barra superior). */
export function principal(page: Page) {
  return page.locator('main#contenido');
}

/** Encabezado CSRF de la sesión del navegador, para preparar datos por API con `page.request`. */
export async function cabecerasApi(page: Page): Promise<Record<string, string>> {
  const cookies = await page.context().cookies();
  const csrf = cookies.find((c) => c.name === 'csrftoken')?.value ?? '';
  return { 'X-CSRFToken': csrf, 'Content-Type': 'application/json' };
}

/** Crea un empleado por API con la sesión actual (preparación de datos, no el CU bajo prueba). Devuelve el id. */
export async function crearEmpleadoApi(page: Page, correo: string, documento: string, nombre = 'Empleado Preparado'): Promise<number> {
  const roles = await (await page.request.get('/api/v1/catalogo/roles')).json();
  const r = await page.request.post('/api/v1/empleados', {
    headers: await cabecerasApi(page),
    data: { nombre, documento, correo, telefono: '3001112233', idRol: roles[0].id },
  });
  expect(r.status()).toBe(201);
  return (await r.json()).id;
}

/** Menú lateral (docs/ui.md): se usa para no confundir sus enlaces con los atajos del contenido. */
export function menu(page: Page) {
  return page.getByRole('navigation', { name: 'Menú principal' });
}

/** Crea un distribuidor por API con la sesión de Gestión (preparación de datos). Devuelve id y código. */
export async function crearDistribuidorApi(page: Page, correo: string, documento: string, nombre: string): Promise<{ id: number; codigo: string }> {
  const r = await page.request.post('/api/v1/distribuidores', {
    headers: await cabecerasApi(page),
    data: { nombre, documento, correo, telefono: '3010000000' },
  });
  expect(r.status()).toBe(201);
  return r.json();
}

/** Registra un ticket por API con la sesión actual (preparación de datos). Devuelve el id. */
export async function crearTicketApi(page: Page, categoria: string, descripcion: string): Promise<number> {
  const r = await page.request.post('/api/v1/tickets', {
    headers: await cabecerasApi(page),
    data: { categoria, descripcion },
  });
  expect(r.status()).toBe(201);
  return (await r.json()).id;
}
