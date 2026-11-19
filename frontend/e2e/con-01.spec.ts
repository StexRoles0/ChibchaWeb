import { expect, test } from '@playwright/test';
import { GESTION, ingresarComo, menu, registrarCliente, cerrarSesion, SOPORTE } from './apoyo/acciones';

test.describe('CU-CON-01 Consultar básico', () => {
  test('FP: M-16 lista clientes y el filtro busca sin distinguir mayúsculas por nombre, correo o documento', async ({ page }) => {
    const d = await registrarCliente(page);
    await cerrarSesion(page);
    await ingresarComo(page, GESTION, /\/gestion$/);
    const lista = page.waitForResponse((r) => r.url().includes('/api/v1/consultas/CLIENTE') && r.request().method() === 'GET');
    await menu(page).getByRole('link', { name: 'Clientes' }).click();
    expect((await lista).status()).toBe(200);
    const tabla = page.getByRole('table', { name: 'Listado de clientes' });
    await page.getByLabel('Buscar clientes').fill(d.nombre.toUpperCase());
    await expect(tabla.getByRole('row')).toHaveCount(2);
    const fila = tabla.getByRole('row', { name: new RegExp(d.nombre) });
    await expect(fila).toContainText(d.correo);
    await expect(fila).toContainText(d.sitio);
    await expect(fila).toContainText('Chibcha-Oro');
    await page.getByLabel('Buscar clientes').fill(d.correo.toUpperCase());
    await expect(tabla.getByRole('row', { name: new RegExp(d.nombre) })).toBeVisible();
    await page.getByLabel('Buscar clientes').fill('no-existe-ningun-cliente-asi');
    await expect(page.getByText('Ningún cliente coincide con la búsqueda.')).toBeVisible();
  });

  test('FP: el mismo método sirve a empleados (M-12) y distribuidores (M-15) por /consultas', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    for (const [tipo, texto] of [['EMPLEADO', 'Sergio Soporte'], ['DISTRIBUIDOR', 'Andes Digital SAS']]) {
      const r = await page.request.get(`/api/v1/consultas/${tipo}?filtro=${encodeURIComponent(texto.toLowerCase())}`);
      expect(r.status()).toBe(200);
      const filas = await r.json();
      expect(filas.map((f: { titulo: string }) => f.titulo)).toContain(texto);
    }
  });

  test('FA (permisos): Gestión no consulta TICKET (403 SIN_PERMISO) y Soporte no entra a Clientes (403 -> página sin permiso)', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    const t = await page.request.get('/api/v1/consultas/TICKET');
    expect(t.status()).toBe(403);
    expect((await t.json()).codigo).toBe('SIN_PERMISO');
    await cerrarSesion(page);

    await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
    const c = await page.request.get('/api/v1/consultas/CLIENTE');
    expect(c.status()).toBe(403);
    await page.goto('/gestion/clientes');
    await expect(page).toHaveURL(/\/no-autorizado$/);
    await expect(page.getByText(/No tienes permiso/i).first()).toBeVisible();
  });

  test('FA: sin sesión la consulta responde 401 NO_AUTENTICADO', async ({ request }) => {
    const r = await request.get('/api/v1/consultas/CLIENTE');
    expect(r.status()).toBe(401);
    expect((await r.json()).codigo).toBe('NO_AUTENTICADO');
  });
});
