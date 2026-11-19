import { expect, test } from '@playwright/test';
import { crearDistribuidorApi, datosRegistro, GESTION, ingresar, ingresarComo, llenarPaso1, llenarPaso2, llenarPaso3, cerrarSesion } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-DIS-04 Eliminar distribuidor', () => {
  test('FP: confirmación en diálogo, baja lógica, y su código deja de servir en nuevos registros (RN-13)', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id, codigo } = await crearDistribuidorApi(page, `b${u}@correo.co`, `${u}04`, `Distribuidora Baja ${u}`);
    await page.goto('/gestion/distribuidores');
    await page.getByLabel('Buscar distribuidores').fill(`${u}04`);
    await page.getByRole('button', { name: `Eliminar Distribuidora Baja ${u}` }).click();
    const dialogo = page.getByRole('dialog', { name: 'Dar de baja el distribuidor' });
    await expect(dialogo).toContainText(`Distribuidora Baja ${u}`);
    const baja = page.waitForResponse((r) => r.url().endsWith(`/api/v1/distribuidores/${id}`) && r.request().method() === 'DELETE');
    await dialogo.getByRole('button', { name: 'Dar de baja' }).click();
    expect((await baja).status()).toBe(204);
    await expect(page.getByRole('row', { name: new RegExp(`Distribuidora Baja ${u}`) })).toContainText(/inactivo/i);
    expect(sql(`SELECT activo FROM usuario WHERE id=${id}`)).toBe('f');

    // Efecto observable por otro CU: el código ya no sirve al registrarse.
    await cerrarSesion(page);
    const d = datosRegistro({ codigoDistribuidor: codigo });
    await ingresar(page, d.correo);
    await llenarPaso1(page, d);
    await llenarPaso2(page, d);
    await llenarPaso3(page, d);
    await expect(page).toHaveURL(/\/registro\/datos$/);
    await expect(page.locator('#codigoDistribuidor-error')).toBeVisible();
  });

  test('FA: Cancelar el diálogo no da de baja', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id } = await crearDistribuidorApi(page, `c${u}@correo.co`, `${u}05`, `Distribuidora Queda ${u}`);
    await page.goto(`/gestion/distribuidores/${id}`);
    await page.getByRole('button', { name: 'Eliminar' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Cancelar' }).click();
    expect(sql(`SELECT activo FROM usuario WHERE id=${id}`)).toBe('t');
  });
});
