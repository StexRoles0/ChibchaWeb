import { expect, test } from '@playwright/test';
import { GESTION, ingresarComo } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-EMP-02 Crear empleado', () => {
  test('FP: M-13 crea el empleado, lo muestra en el detalle y en el listado, y queda persistido', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/empleados');
    await page.getByRole('link', { name: /Crear empleado/ }).click();
    await expect(page).toHaveURL(/\/gestion\/empleados\/nuevo$/);

    await page.getByLabel('Nombre completo').fill(`Empleado Nuevo ${u}`);
    await page.getByLabel('Documento de identidad').fill(`E-${u}`);
    await page.getByLabel('Correo electrónico').fill(`nuevo${u}@chibchaweb.co`);
    await page.getByLabel('Teléfono').fill('3105556677');
    await page.getByLabel('Cargo').selectOption({ label: 'Soporte' });
    const creado = page.waitForResponse((r) => r.url().endsWith('/api/v1/empleados') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Guardar' }).click();
    const r = await creado;
    expect(r.status()).toBe(201);
    expect(typeof (await r.json()).id).toBe('number');
    await expect(page).toHaveURL(/\/gestion\/empleados\/\d+$/); // va al detalle (M-14)
    await expect(page.getByRole('heading', { name: `Empleado Nuevo ${u}` })).toBeVisible();

    await page.goto('/gestion/empleados');
    await page.getByLabel('Buscar empleados').fill(`E-${u}`);
    await expect(page.getByRole('row', { name: new RegExp(`Empleado Nuevo ${u}`) })).toBeVisible();
    expect(sql(`SELECT r.nombre, u.activo FROM empleado e JOIN usuario u ON u.id=e.id JOIN rol r ON r.id=e.id_rol WHERE e.documento='E-${u}'`)).toBe('Soporte|t');
  });

  test('FA: correo y documento duplicados -> 409 DUPLICADO con el campo, bajo el campo correspondiente', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/empleados/nuevo');
    await page.getByLabel('Nombre completo').fill('Duplicado Uno');
    await page.getByLabel('Documento de identidad').fill(`E-${u}`);
    await page.getByLabel('Correo electrónico').fill(GESTION); // correo ya existente
    await page.getByLabel('Teléfono').fill('3000000000');
    await page.getByLabel('Cargo').selectOption({ label: 'Soporte' });
    let envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/empleados') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Guardar' }).click();
    let r = await envio;
    expect(r.status()).toBe(409);
    expect(await r.json()).toMatchObject({ codigo: 'DUPLICADO', campo: 'correo' });
    await expect(page.locator('#correo-error')).toBeVisible();

    await page.getByLabel('Correo electrónico').fill(`otro${u}@chibchaweb.co`);
    await page.getByLabel('Documento de identidad').fill('E-1001'); // documento ya existente
    envio = page.waitForResponse((x) => x.url().endsWith('/api/v1/empleados') && x.request().method() === 'POST');
    await page.getByRole('button', { name: 'Guardar' }).click();
    r = await envio;
    expect(r.status()).toBe(409);
    expect(await r.json()).toMatchObject({ codigo: 'DUPLICADO', campo: 'documento' });
    await expect(page.locator('#documento-error')).toBeVisible();
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='otro${u}@chibchaweb.co'`)).toBe('0');
  });

  test('FA: campos obligatorios vacíos no se envían', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/empleados/nuevo');
    await page.getByRole('button', { name: 'Guardar' }).click();
    await expect(page.locator('#nombre-error')).toBeVisible();
    await expect(page).toHaveURL(/\/nuevo$/);
  });
});
