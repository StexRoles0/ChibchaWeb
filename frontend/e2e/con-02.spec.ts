import { expect, test } from '@playwright/test';
import { cerrarSesion, crearDistribuidorApi, crearTicketApi, GESTION, ingresarComo, registrarCliente, SOPORTE } from './apoyo/acciones';
import { unico } from './apoyo/entorno';

test.describe('CU-CON-02 Consultar detalle', () => {
  test('FP: M-16 abre el panel de detalle de un cliente con datos personales, hospedaje y facturación', async ({ page }) => {
    const d = await registrarCliente(page, { codigoDistribuidor: 'DIS-ANDES1' });
    await cerrarSesion(page);
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/clientes');
    await page.getByLabel('Buscar clientes').fill(d.correo);
    const detalle = page.waitForResponse((r) => /\/api\/v1\/consultas\/CLIENTE\/\d+$/.test(r.url()));
    await page.getByRole('button', { name: new RegExp(`Ver detalle de ${d.nombre}`) }).click();
    expect((await detalle).status()).toBe(200);
    const panel = page.getByRole('complementary');
    await expect(panel.getByRole('heading', { name: d.nombre })).toBeVisible();
    for (const t of [d.correo, d.telefono, 'Calle 10 # 5-20, Sogamoso', 'DIS-ANDES1', `${d.sitio}.chibchaweb.`, 'Chibcha-Oro', 'Semestral', 'VISA •••• 4242']) {
      await expect(panel).toContainText(t);
    }
  });

  test('FP: M-14 muestra el detalle de empleado y de distribuidor (código y categoría)', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/gestion/empleados');
    await page.getByLabel('Buscar empleados').fill('sergio');
    await page.getByRole('link', { name: 'Ver Sergio Soporte' }).click();
    await expect(page.getByRole('heading', { name: 'Sergio Soporte' })).toBeVisible();
    await expect(page.getByText('E-1002')).toBeVisible();
    await expect(page.getByText('soporte@chibchaweb.co')).toBeVisible();

    const { id, codigo } = await crearDistribuidorApi(page, `d${u}@correo.co`, `${u}06`, `Distribuidora Detalle ${u}`);
    await page.goto(`/gestion/distribuidores/${id}`);
    await expect(page.getByText(codigo, { exact: true })).toBeVisible();
    await expect(page.getByText('Referidos')).toBeVisible();
    await expect(page.getByText('Categoría')).toBeVisible();
  });

  test('FP: Soporte ve el detalle de un ticket con descripción y movimientos (M-17)', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearTicketApi(page, 'OTRA', `Ticket para consultar detalle ${u}`);
    await cerrarSesion(page);
    await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
    await page.goto(`/soporte/tickets/${id}`);
    const detalle = page.getByLabel('Detalle del ticket');
    await expect(detalle.getByRole('heading', { name: `Ticket #${id}` })).toBeVisible();
    await expect(detalle).toContainText(`Ticket para consultar detalle ${u}`);
    await expect(detalle).toContainText('Gabriela Gestión');
    await expect(detalle.getByText('Aún no tiene movimientos.')).toBeVisible();
  });

  test('FA: detalle de un id inexistente -> 404 NO_ENCONTRADO', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    const r = await page.request.get('/api/v1/consultas/EMPLEADO/99999999');
    expect(r.status()).toBe(404);
    expect((await r.json()).codigo).toBe('NO_ENCONTRADO');
    await page.goto('/gestion/empleados/99999999');
    await expect(page.getByText(/No encontramos el empleado/)).toBeVisible();
  });
});
