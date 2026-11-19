import { expect, Page, test } from '@playwright/test';
import { ADMIN, cabecerasApi, cerrarSesion, GESTION, ingresarComo, menu } from './apoyo/acciones';
import { sql } from './apoyo/entorno';

// Una sola migración real por BD: la segunda da REVERTIDA por duplicados (D-06). Las pruebas dependen del orden.
test.describe.configure({ mode: 'serial' });

const yaMigrado = () => sql(`SELECT count(*) FROM usuario WHERE correo='marta.rojas@ejemplo.co'`) !== '0';

async function irAMigracion(page: Page) {
  await ingresarComo(page, ADMIN, /\/admin$/);
  await menu(page).getByRole('link', { name: 'Migración' }).click();
  await expect(page.getByRole('heading', { name: 'Migración de datos legados' })).toBeVisible();
}

async function simular(page: Page, nombre: string) {
  const sim = page.waitForResponse((r) => r.url().endsWith('/api/v1/migraciones') && r.request().method() === 'POST');
  await page.getByRole('button', { name: nombre }).click();
  const r = await sim;
  expect(r.status()).toBe(201);
  return r.json() as Promise<{ idProceso: number; validos: number; invalidos: number; entradas: string[] }>;
}

test.describe('CU-MIG-01 Migrar registros legados', () => {
  test('FP: simulación (log INFO/ERROR, sin escribir datos) y migración real EJECUTADA', async ({ page }) => {
    test.skip(yaMigrado(), 'El entorno ya tiene la migración real: recrea la BD e2e (npm run e2e).');
    await irAMigracion(page);
    await expect(page.getByRole('button', { name: 'Ejecutar migración real' })).toHaveCount(0); // sin simulación no hay botón

    const resultado = await simular(page, 'Ejecutar simulación');
    expect(resultado.validos).toBeGreaterThan(0);
    expect(resultado.invalidos).toBeGreaterThan(0);
    // La simulación no escribe datos de negocio (RN-26).
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='marta.rojas@ejemplo.co'`)).toBe('0');

    const log = page.getByRole('region', { name: 'Log de la simulación' });
    await expect(log.getByRole('row', { name: /INFO.*CLIENTE.*L-001/ })).toBeVisible();
    await expect(log.getByRole('row', { name: /ERROR.*CLIENTE.*L-006/ })).toBeVisible();
    await expect(page.getByText(`${resultado.validos} registros válidos · ${resultado.invalidos} inválidos`)).toBeVisible();
    await expect(log.locator('tr.info, tr.error').first()).toBeVisible();

    await page.getByRole('button', { name: 'Ejecutar migración real' }).click();
    const dialogo = page.getByRole('dialog', { name: 'Ejecutar la migración real' });
    await expect(dialogo).toContainText(`${resultado.validos} registros válidos`);
    const conf = page.waitForResponse((r) => r.url().endsWith(`/api/v1/migraciones/${resultado.idProceso}/confirmacion`));
    await dialogo.getByRole('button', { name: 'Ejecutar migración' }).click();
    const r = await conf;
    expect(r.status()).toBe(200);
    expect(await r.json()).toEqual({ estado: 'EJECUTADA' });
    await expect(page.getByRole('status').filter({ hasText: 'Migración ejecutada' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ejecutar migración real' })).toBeDisabled();

    // Persistido: los clientes válidos existen (sin cuenta de acceso, RN-28) y los inválidos no.
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='marta.rojas@ejemplo.co' AND tipo='CLIENTE'`)).toBe('1');
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='correo-sin-arroba'`)).toBe('0');
    expect(sql(`SELECT count(*) FROM cuenta_acceso c JOIN usuario u ON u.id=c.id_titular WHERE u.correo='marta.rojas@ejemplo.co'`)).toBe('0');
    expect(sql(`SELECT estado FROM proceso_migracion WHERE id=${resultado.idProceso}`)).toBe('EJECUTADA');
    // Y por la interfaz de Gestión: el cliente migrado se encuentra en M-16.
    await cerrarSesion(page);
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/clientes');
    await page.getByLabel('Buscar clientes').fill('marta.rojas@ejemplo.co');
    await expect(page.getByRole('row', { name: /Marta Rojas/ })).toBeVisible();
  });

  test('FA: una segunda migración real da REVERTIDA por duplicados y no cambia nada', async ({ page }) => {
    const antes = sql(`SELECT count(*) FROM usuario`);
    await irAMigracion(page);
    const resultado = await simular(page, 'Ejecutar simulación');
    await page.getByRole('button', { name: 'Ejecutar migración real' }).click();
    const conf = page.waitForResponse((r) => r.url().endsWith(`/api/v1/migraciones/${resultado.idProceso}/confirmacion`));
    await page.getByRole('dialog').getByRole('button', { name: 'Ejecutar migración' }).click();
    expect((await (await conf).json())).toEqual({ estado: 'REVERTIDA' });
    await expect(page.getByRole('alert').filter({ hasText: 'La migración quedó revertida' })).toBeVisible();
    expect(sql(`SELECT count(*) FROM usuario`)).toBe(antes);
    expect(sql(`SELECT estado FROM proceso_migracion WHERE id=${resultado.idProceso}`)).toBe('REVERTIDA');
  });

  test('FA: Cancelar la migración -> CANCELADA y no se escribe nada', async ({ page }) => {
    const antes = sql(`SELECT count(*) FROM usuario`);
    await irAMigracion(page);
    const resultado = await simular(page, 'Ejecutar simulación');
    await page.getByRole('button', { name: 'Cancelar migración' }).click();
    const cancel = page.waitForResponse((r) => r.url().endsWith(`/api/v1/migraciones/${resultado.idProceso}/cancelacion`));
    await page.getByRole('dialog', { name: 'Cancelar la migración' }).getByRole('button', { name: 'Cancelar migración' }).click();
    expect(await (await cancel).json()).toEqual({ estado: 'CANCELADA' });
    await expect(page.getByRole('status').filter({ hasText: 'Migración cancelada' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Ejecutar migración real' })).toBeDisabled();
    expect(sql(`SELECT count(*) FROM usuario`)).toBe(antes);
    expect(sql(`SELECT estado FROM proceso_migracion WHERE id=${resultado.idProceso}`)).toBe('CANCELADA');
  });

  test('FA: confirmar dos veces o sobre un proceso cancelado -> 409 ESTADO_INVALIDO', async ({ page }) => {
    await ingresarComo(page, ADMIN, /\/admin$/);
    const h = await cabecerasApi(page);
    const sim = await page.request.post('/api/v1/migraciones', { headers: h });
    const { idProceso } = await sim.json();
    const cancel = await page.request.post(`/api/v1/migraciones/${idProceso}/cancelacion`, { headers: h });
    expect(cancel.status()).toBe(200);
    for (const accion of ['confirmacion', 'cancelacion']) {
      const r = await page.request.post(`/api/v1/migraciones/${idProceso}/${accion}`, { headers: h });
      expect(r.status()).toBe(409);
      expect((await r.json()).codigo).toBe('ESTADO_INVALIDO');
    }
    const inexistente = await page.request.post('/api/v1/migraciones/99999999/confirmacion', { headers: h });
    expect(inexistente.status()).toBe(404);
  });
});
