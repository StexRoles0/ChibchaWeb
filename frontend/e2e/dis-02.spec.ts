import { expect, test } from '@playwright/test';
import { GESTION, ingresarComo } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-DIS-02 Crear distribuidor', () => {
  test('FP: M-13 (modo distribuidor) genera el código DIS-XXXXXX y aparece en el detalle y el listado', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/distribuidores');
    await page.getByRole('link', { name: /Crear distribuidor/ }).click();
    await expect(page).toHaveURL(/\/gestion\/distribuidores\/nuevo$/);
    await expect(page.getByLabel('Cargo')).toHaveCount(0); // el distribuidor no tiene cargo
    await page.getByLabel('Nombre o razón social').fill(`Distribuidora Nueva ${u}`);
    await page.getByLabel('Documento de identidad').fill(`${u}01`);
    await page.getByLabel('Correo electrónico').fill(`nueva${u}@correo.co`);
    await page.getByLabel('Teléfono').fill('3010000000');
    const creado = page.waitForResponse((r) => r.url().endsWith('/api/v1/distribuidores') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Guardar' }).click();
    const r = await creado;
    expect(r.status()).toBe(201);
    const { codigo } = await r.json();
    expect(codigo).toMatch(/^DIS-[A-Z0-9]{6}$/);

    await expect(page).toHaveURL(/\/gestion\/distribuidores\/\d+$/);
    await expect(page.getByRole('heading', { name: `Distribuidora Nueva ${u}` })).toBeVisible();
    await expect(page.getByText(codigo, { exact: true })).toBeVisible();

    await page.goto('/gestion/distribuidores');
    await page.getByLabel('Buscar distribuidores').fill(`${u}01`);
    await expect(page.getByRole('row', { name: new RegExp(codigo) })).toBeVisible();
    expect(sql(`SELECT codigo FROM distribuidor WHERE documento='${u}01'`)).toBe(codigo);
  });

  test('FA: documento o correo duplicado -> 409 DUPLICADO con el campo', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/distribuidores/nuevo');
    await page.getByLabel('Nombre o razón social').fill('Duplicada');
    await page.getByLabel('Documento de identidad').fill('900123456'); // el del distribuidor sembrado
    await page.getByLabel('Correo electrónico').fill(`dupdis${u}@correo.co`);
    await page.getByLabel('Teléfono').fill('3010000000');
    const envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/distribuidores') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Guardar' }).click();
    const r = await envio;
    expect(r.status()).toBe(409);
    expect(await r.json()).toMatchObject({ codigo: 'DUPLICADO', campo: 'documento' });
    await expect(page.locator('#documento-error')).toBeVisible();
  });
});
