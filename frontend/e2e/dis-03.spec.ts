import { expect, test } from '@playwright/test';
import { crearDistribuidorApi, GESTION, ingresarComo } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-DIS-03 Modificar distribuidor', () => {
  test('FP: Editar precarga, PUT guarda; el código no cambia y el detalle muestra los datos nuevos', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id, codigo } = await crearDistribuidorApi(page, `m${u}@correo.co`, `${u}02`, `Distribuidora Modificable ${u}`);
    await page.goto('/gestion/distribuidores');
    await page.getByLabel('Buscar distribuidores').fill(`${u}02`);
    await page.getByRole('link', { name: `Editar Distribuidora Modificable ${u}` }).click();
    await expect(page).toHaveURL(new RegExp(`/gestion/distribuidores/${id}/editar$`));
    await expect(page.getByLabel('Documento de identidad')).toHaveValue(`${u}02`);

    await page.getByLabel('Nombre o razón social').fill(`Distribuidora Renombrada ${u}`);
    await page.getByLabel('Teléfono').fill('6011112222');
    const put = page.waitForResponse((r) => r.url().endsWith(`/api/v1/distribuidores/${id}`) && r.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Guardar' }).click();
    expect((await put).status()).toBe(204);
    await expect(page.getByRole('heading', { name: `Distribuidora Renombrada ${u}` })).toBeVisible();
    await expect(page.getByText('6011112222')).toBeVisible();
    await expect(page.getByText(codigo, { exact: true })).toBeVisible();
    expect(sql(`SELECT u.nombre, d.codigo FROM usuario u JOIN distribuidor d ON d.id=u.id WHERE u.id=${id}`)).toBe(`Distribuidora Renombrada ${u}|${codigo}`);
  });

  test('FA: correo ya usado por otro usuario -> 409 DUPLICADO bajo el campo', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id } = await crearDistribuidorApi(page, `n${u}@correo.co`, `${u}03`, `Distribuidora Choque ${u}`);
    await page.goto(`/gestion/distribuidores/${id}/editar`);
    await page.getByLabel('Correo electrónico').fill('contacto@andesdigital.co');
    const put = page.waitForResponse((r) => r.url().endsWith(`/api/v1/distribuidores/${id}`) && r.request().method() === 'PUT');
    await page.getByRole('button', { name: 'Guardar' }).click();
    const r = await put;
    expect(r.status()).toBe(409);
    expect(await r.json()).toMatchObject({ codigo: 'DUPLICADO', campo: 'correo' });
    await expect(page.locator('#correo-error')).toBeVisible();
  });
});
