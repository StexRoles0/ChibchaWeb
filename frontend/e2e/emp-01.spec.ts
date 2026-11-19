import { expect, test } from '@playwright/test';
import { crearEmpleadoApi, GESTION, ingresarComo, menu } from './apoyo/acciones';
import { unico } from './apoyo/entorno';

test.describe('CU-EMP-01 Gestionar empleado', () => {
  test('FP: M-12 lista los empleados con búsqueda sin distinguir mayúsculas por nombre, correo o documento', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await crearEmpleadoApi(page, `buscable${u}@chibchaweb.co`, `DOC-${u}`, `Marisol Buscable ${u}`);

    const lista = page.waitForResponse((r) => r.url().includes('/api/v1/empleados') && r.request().method() === 'GET');
    await menu(page).getByRole('link', { name: 'Empleados' }).click();
    expect((await lista).status()).toBe(200);
    await expect(page).toHaveURL(/\/gestion\/empleados$/);
    await expect(page.getByRole('heading', { name: 'Empleados' })).toBeVisible();
    const tabla = page.getByRole('table', { name: 'Listado de empleados' });
    await expect(tabla.getByRole('row', { name: /Gabriela Gestión/ })).toBeVisible();
    await expect(tabla.getByRole('row', { name: /Sergio Soporte/ })).toBeVisible();

    const buscar = page.getByLabel('Buscar empleados');
    await buscar.fill(`MARISOL BUSCABLE ${u}`.toUpperCase()); // por nombre, en mayúsculas
    await expect(tabla.getByRole('row')).toHaveCount(2); // encabezado + 1
    await expect(tabla.getByRole('row', { name: new RegExp(`Marisol Buscable ${u}`) })).toBeVisible();
    await expect(page.getByText('Mostrando 1 registro')).toBeVisible();

    await buscar.fill(`BUSCABLE${u}@CHIBCHAWEB.CO`); // por correo
    await expect(tabla.getByRole('row', { name: new RegExp(`Marisol Buscable ${u}`) })).toBeVisible();
    await buscar.fill(`doc-${u}`); // por documento
    await expect(tabla.getByRole('row', { name: new RegExp(`Marisol Buscable ${u}`) })).toBeVisible();
    await expect(tabla.getByRole('row')).toHaveCount(2);

    await buscar.fill(`sin-coincidencias-${u}`);
    await expect(page.getByText('Ningún', { exact: false }).first()).toBeVisible();
    await expect(page.getByText('Mostrando 0 registros')).toBeVisible();
  });
});
