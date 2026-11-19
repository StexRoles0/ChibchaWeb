import { expect, test } from '@playwright/test';
import { registrarCliente } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-DOM-02 Generar y enviar solicitud XML', () => {
  test('FP: el mismo POST genera el XML y la solicitud pasa de REGISTRADA a ENVIADA con fecha de envío', async ({ page }) => {
    const u = unico();
    const d = await registrarCliente(page);
    await page.goto('/cliente/dominios');
    await page.getByLabel('Nombre del dominio').fill(`xml${u}`);
    await page.getByLabel('Extensión').selectOption('.org');
    const envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/dominios/solicitudes') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    expect(await (await envio).json()).toMatchObject({ estado: 'ENVIADA' });
    await expect(page.getByRole('status').filter({ hasText: `xml${u}.org` })).toBeVisible();
    expect(sql(`SELECT s.estado, s.fecha_envio >= s.fecha_solicitud FROM solicitud_dominio s JOIN usuario u ON u.id=s.id_solicitante WHERE u.correo='${d.correo}'`)).toBe('ENVIADA|t');
  });

  test('FA: registrador caído (dominio con "rechazo") -> 201 con estado FALLIDA y aviso; puede enviar una nueva', async ({ page }) => {
    const u = unico();
    const d = await registrarCliente(page);
    await page.goto('/cliente/dominios');
    await page.getByLabel('Nombre del dominio').fill(`rechazo${u}`);
    await page.getByLabel('Extensión').selectOption('.com');
    const envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/dominios/solicitudes') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    const r = await envio;
    expect(r.status()).toBe(201);
    expect(await r.json()).toMatchObject({ estado: 'FALLIDA' });
    await expect(page.getByRole('alert').filter({ hasText: 'quedó como fallida' })).toContainText(`rechazo${u}.com`);
    const tabla = page.getByRole('table', { name: 'Solicitudes de dominio' });
    await expect(tabla.getByRole('row', { name: new RegExp(`rechazo${u}\\.com`) })).toContainText(/fallida/i);
    expect(sql(`SELECT s.estado, s.fecha_envio IS NULL FROM solicitud_dominio s JOIN usuario u ON u.id=s.id_solicitante WHERE u.correo='${d.correo}'`)).toBe('FALLIDA|t');

    // Una solicitud nueva sí se envía.
    await page.getByLabel('Nombre del dominio').fill(`bueno${u}`);
    await page.getByRole('button', { name: 'Enviar solicitud' }).click();
    await expect(tabla.getByRole('row', { name: new RegExp(`bueno${u}\\.com`) })).toContainText(/enviada/i);
    expect(sql(`SELECT count(*) FROM solicitud_dominio s JOIN usuario u ON u.id=s.id_solicitante WHERE u.correo='${d.correo}'`)).toBe('2');
  });
});
