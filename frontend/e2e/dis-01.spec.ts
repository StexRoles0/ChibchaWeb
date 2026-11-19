import { expect, test } from '@playwright/test';
import { crearDistribuidorApi, GESTION, ingresarComo, menu } from './apoyo/acciones';
import { unico } from './apoyo/entorno';

test.describe('CU-DIS-01 Gestionar distribuidor', () => {
  test('FP: M-15 lista distribuidores con código y referidos, y la búsqueda filtra', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { codigo } = await crearDistribuidorApi(page, `dis${u}@correo.co`, `${u}00`, `Distribuidora Buscable ${u}`);

    const lista = page.waitForResponse((r) => r.url().includes('/api/v1/distribuidores') && r.request().method() === 'GET');
    await menu(page).getByRole('link', { name: 'Distribuidores' }).click();
    expect((await lista).status()).toBe(200);
    await expect(page).toHaveURL(/\/gestion\/distribuidores$/);
    const tabla = page.getByRole('table', { name: 'Listado de distribuidores' });
    const sembrado = tabla.getByRole('row', { name: /Andes Digital SAS/ });
    await expect(sembrado).toContainText('DIS-ANDES1');
    await expect(sembrado).toContainText(/referidos/);

    await page.getByLabel('Buscar distribuidores').fill(`BUSCABLE ${u}`);
    await expect(tabla.getByRole('row')).toHaveCount(2);
    await expect(tabla.getByRole('row', { name: new RegExp(`Distribuidora Buscable ${u}`) })).toContainText(codigo);
    await expect(sembrado).toHaveCount(0);
  });
});
