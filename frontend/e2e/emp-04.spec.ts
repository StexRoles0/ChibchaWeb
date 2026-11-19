import { expect, test } from '@playwright/test';
import { crearEmpleadoApi, GESTION, ingresarComo } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-EMP-04 Eliminar empleado', () => {
  test('FP: Eliminar pide confirmación en un diálogo y hace la baja lógica (el registro se conserva)', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearEmpleadoApi(page, `baja${u}@chibchaweb.co`, `E-${u}`, `Empleado Baja ${u}`);
    await page.goto('/gestion/empleados');
    await page.getByLabel('Buscar empleados').fill(`E-${u}`);
    await page.getByRole('button', { name: `Eliminar Empleado Baja ${u}` }).click();

    const dialogo = page.getByRole('dialog', { name: 'Dar de baja el empleado' });
    await expect(dialogo).toContainText(`Empleado Baja ${u}`);
    const baja = page.waitForResponse((r) => r.url().endsWith(`/api/v1/empleados/${id}`) && r.request().method() === 'DELETE');
    await dialogo.getByRole('button', { name: 'Dar de baja' }).click();
    expect((await baja).status()).toBe(204);
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page.getByRole('status').filter({ hasText: `Se dio de baja a Empleado Baja ${u}` })).toBeVisible();

    // La fila sigue (baja lógica), con estado inactivo y sin poder eliminarse otra vez.
    const fila = page.getByRole('row', { name: new RegExp(`Empleado Baja ${u}`) });
    await expect(fila).toContainText(/inactivo/i);
    await expect(page.getByRole('button', { name: `Eliminar Empleado Baja ${u}` })).toBeDisabled();
    expect(sql(`SELECT activo FROM usuario WHERE id=${id}`)).toBe('f');
    // Por otro endpoint: el detalle sigue existiendo.
    const detalle = await page.request.get(`/api/v1/empleados/${id}`);
    expect(detalle.status()).toBe(200);
  });

  test('FA: Cancelar el diálogo no da de baja', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearEmpleadoApi(page, `quedo${u}@chibchaweb.co`, `E-${u}`, `Empleado Queda ${u}`);
    await page.goto(`/gestion/empleados/${id}`);
    await page.getByRole('button', { name: 'Eliminar' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Cancelar' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    expect(sql(`SELECT activo FROM usuario WHERE id=${id}`)).toBe('t');
  });

  test('FP: la baja desde el detalle (M-14) también funciona', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearEmpleadoApi(page, `det${u}@chibchaweb.co`, `E-${u}`, `Empleado Detalle ${u}`);
    await page.goto(`/gestion/empleados/${id}`);
    await page.getByRole('button', { name: 'Eliminar' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Dar de baja' }).click();
    await expect(page.getByRole('button', { name: 'Eliminar' })).toBeDisabled();
    expect(sql(`SELECT activo FROM usuario WHERE id=${id}`)).toBe('f');
  });
});
