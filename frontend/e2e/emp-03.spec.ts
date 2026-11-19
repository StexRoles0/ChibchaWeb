import { expect, test } from '@playwright/test';
import { crearEmpleadoApi, GESTION, ingresarComo } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-EMP-03 Modificar empleado', () => {
  test('FP: Editar precarga el formulario, PUT guarda y el detalle y el listado muestran el cambio', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearEmpleadoApi(page, `mod${u}@chibchaweb.co`, `E-${u}`, `Empleado Modificable ${u}`);
    await page.goto('/gestion/empleados');
    await page.getByLabel('Buscar empleados').fill(`E-${u}`);
    await page.getByRole('link', { name: `Editar Empleado Modificable ${u}` }).click();
    await expect(page).toHaveURL(new RegExp(`/gestion/empleados/${id}/editar$`));
    await expect(page.getByLabel('Documento de identidad')).toHaveValue(`E-${u}`);
    await expect(page.getByLabel('Correo electrónico')).toHaveValue(`mod${u}@chibchaweb.co`);

    await page.getByLabel('Nombre completo').fill(`Empleado Renombrado ${u}`);
    await page.getByLabel('Teléfono').fill('3119998877');
    const put = page.waitForResponse((r) => r.url().endsWith(`/api/v1/empleados/${id}`) && r.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Guardar' }).click();
    expect((await put).status()).toBe(204);
    await expect(page).toHaveURL(new RegExp(`/gestion/empleados/${id}$`));
    await expect(page.getByRole('heading', { name: `Empleado Renombrado ${u}` })).toBeVisible();
    await expect(page.getByText('3119998877')).toBeVisible();
    expect(sql(`SELECT u.nombre, u.telefono FROM usuario u WHERE u.correo='mod${u}@chibchaweb.co'`)).toBe(`Empleado Renombrado ${u}|3119998877`);
  });

  test('FA: cambiar el correo por uno que ya existe -> 409 DUPLICADO bajo el campo y nada cambia', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearEmpleadoApi(page, `dup${u}@chibchaweb.co`, `E-${u}`, `Empleado Duplicable ${u}`);
    await page.goto(`/gestion/empleados/${id}/editar`);
    await page.getByLabel('Correo electrónico').fill('soporte@chibchaweb.co');
    const put = page.waitForResponse((r) => r.url().endsWith(`/api/v1/empleados/${id}`) && r.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Guardar' }).click();
    const r = await put;
    expect(r.status()).toBe(409);
    expect(await r.json()).toMatchObject({ codigo: 'DUPLICADO', campo: 'correo' });
    await expect(page.locator('#correo-error')).toBeVisible();
    expect(sql(`SELECT correo FROM usuario WHERE id=${id}`)).toBe(`dup${u}@chibchaweb.co`);
  });
});
