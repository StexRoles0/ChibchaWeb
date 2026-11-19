import { expect, test } from '@playwright/test';
import { cabecerasApi, cerrarSesion, GESTION, ingresarComo, menu, registrarCliente } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-SOP-01 Registrar ticket', () => {
  test('FP (cliente): M-10 registra el ticket ABIERTO en el nivel 1, con su sitio, y aparece en Mis tickets', async ({ page }) => {
    const u = unico();
    const d = await registrarCliente(page);
    await menu(page).getByRole('link', { name: 'Soporte' }).click();
    await expect(page).toHaveURL(/\/cliente\/soporte$/);
    await expect(page.getByText('Todavía no has reportado ninguna novedad.')).toBeVisible();

    await page.getByLabel('Tipo de novedad').selectOption('RENDIMIENTO');
    await page.getByLabel(/Sitio afectado/).selectOption({ index: 1 }); // el único sitio del cliente
    await page.getByLabel('Describe el problema').fill(`El sitio tarda en cargar ${u}`);
    const envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/tickets') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Enviar ticket' }).click();
    const r = await envio;
    expect(r.status()).toBe(201);
    const { id } = await r.json();
    await expect(page.getByRole('status').filter({ hasText: `Ticket #${id} registrado` })).toBeVisible();

    const tabla = page.getByRole('table', { name: 'Mis tickets' });
    const fila = tabla.getByRole('row', { name: new RegExp(`#${id}`) });
    await expect(fila).toContainText('Rendimiento');
    await expect(fila).toContainText(/abierto/i);
    expect(sql(`SELECT t.estado, n.orden, t.categoria, t.id_sitio_afectado IS NOT NULL FROM ticket t JOIN nivel_servicio n ON n.id=t.id_nivel_actual JOIN usuario u ON u.id=t.id_reportante WHERE u.correo='${d.correo}'`)).toBe('ABIERTO|1|RENDIMIENTO|t');
  });

  test('FP (empleado): cualquier empleado reporta una novedad desde /soporte/reportar, sin selector de sitio', async ({ page }) => {
    const u = unico();
    await ingresarComo(page, GESTION, /\/gestion$/);
    await menu(page).getByRole('link', { name: 'Reportar novedad' }).click();
    await expect(page).toHaveURL(/\/soporte\/reportar$/);
    await expect(page.getByLabel(/Sitio afectado/)).toHaveCount(0);
    await page.getByLabel('Tipo de novedad').selectOption('CORREO');
    await page.getByLabel('Describe el problema').fill(`Novedad de gestión ${u}`);
    await page.getByRole('button', { name: 'Enviar ticket' }).click();
    const tabla = page.getByRole('table', { name: 'Mis tickets' });
    await expect(tabla.getByRole('row', { name: /Correo/ }).first()).toContainText(/abierto/i);
    expect(sql(`SELECT t.estado, n.orden FROM ticket t JOIN nivel_servicio n ON n.id=t.id_nivel_actual WHERE t.descripcion='Novedad de gestión ${u}'`)).toBe('ABIERTO|1');
  });

  test('FA: descripción vacía no se envía; y un sitio ajeno es rechazado por el backend (422)', async ({ page, context }) => {
    const otro = await registrarCliente(page);
    const sitioAjeno = sql(`SELECT s.id_sitio FROM suscripcion s JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${otro.correo}'`);
    await cerrarSesion(page);
    await context.clearCookies();

    await registrarCliente(page);
    await page.goto('/cliente/soporte');
    await page.getByRole('button', { name: 'Enviar ticket' }).click();
    await expect(page.locator('#descripcion-error')).toBeVisible();

    const r = await page.request.post('/api/v1/tickets', {
      headers: await cabecerasApi(page),
      data: { categoria: 'OTRA', descripcion: 'Sitio que no es mío', idSitio: Number(sitioAjeno) },
    });
    expect(r.status()).toBe(422);
    expect((await r.json()).codigo).toMatch(/VALIDACION|REGLA_NEGOCIO/);
  });
});
