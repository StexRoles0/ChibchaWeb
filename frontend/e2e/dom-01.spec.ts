import { expect, test } from '@playwright/test';
import { cabecerasApi, menu, registrarCliente } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

async function solicitar(page: import('@playwright/test').Page, nombre: string, extension: string) {
  await page.getByLabel('Nombre del dominio').fill(nombre);
  await page.getByLabel('Extensión').selectOption(extension);
  const envio = page.waitForResponse((r) => r.url().endsWith('/api/v1/dominios/solicitudes') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Enviar solicitud' }).click();
  return envio;
}

test.describe('CU-DOM-01 Registrar solicitud de dominio', () => {
  test('FP: M-09 registra la solicitud, queda ENVIADA y aparece en la tabla del historial', async ({ page }) => {
    const u = unico();
    const d = await registrarCliente(page);
    await menu(page).getByRole('link', { name: 'Dominios' }).click();
    await expect(page.getByRole('heading', { name: 'Solicitar un dominio' })).toBeVisible();
    await expect(page.getByText('Aún no has solicitado ningún dominio.')).toBeVisible();

    await page.getByLabel('Nombre del dominio').fill(`Mi-Tienda${u}`);
    await expect(page.getByText(`mi-tienda${u}.com tiene un formato válido.`.replace('mi-tienda', 'Mi-Tienda'), { exact: false })).toBeVisible();
    const r = await solicitar(page, `Mi-Tienda${u}`, '.co');
    expect(r.status()).toBe(201);
    expect(await r.json()).toMatchObject({ estado: 'ENVIADA' });
    await expect(page.getByRole('status').filter({ hasText: 'enviada al registrador' })).toBeVisible();

    // Persistido: la tabla se refresca (GET /dominios/solicitudes) y el nombre se guarda en minúsculas (RN-16).
    const tabla = page.getByRole('table', { name: 'Solicitudes de dominio' });
    await expect(tabla.getByRole('row', { name: new RegExp(`mi-tienda${u}\\.co`) })).toContainText(/enviada/i);
    expect(sql(`SELECT s.nombre, s.extension, s.estado, s.fecha_envio IS NOT NULL FROM solicitud_dominio s JOIN usuario u ON u.id=s.id_solicitante WHERE u.correo='${d.correo}'`)).toBe(`mi-tienda${u}|.co|ENVIADA|t`);
  });

  test('FA: formato inválido -> la interfaz no envía y el backend responde 422 VALIDACION; no se guarda nada', async ({ page }) => {
    const d = await registrarCliente(page);
    await page.goto('/cliente/dominios');
    const nombres = ['-guion-al-inicio', 'guion-al-final-', 'con espacio', 'a'.repeat(64)];

    // La validación del frontend es solo ayuda: avisa y no manda la petición.
    let enviado = false;
    page.on('request', (r) => { if (r.url().endsWith('/api/v1/dominios/solicitudes') && r.method() === 'POST') enviado = true; });
    for (const n of nombres) {
      await page.getByLabel('Nombre del dominio').fill(n);
      await page.getByRole('button', { name: 'Enviar solicitud' }).click();
      await expect(page.locator('#nombre-error')).toBeVisible();
    }
    expect(enviado).toBe(false);

    // El backend vuelve a validar (RN-16): 422 y sin registro.
    for (const nombre of nombres) {
      const r = await page.request.post('/api/v1/dominios/solicitudes', { headers: await cabecerasApi(page), data: { nombre, extension: '.com' } });
      expect(r.status()).toBe(422);
      expect((await r.json()).codigo).toBe('VALIDACION');
    }
    const ext = await page.request.post('/api/v1/dominios/solicitudes', { headers: await cabecerasApi(page), data: { nombre: 'valido', extension: '.xyz' } });
    expect(ext.status()).toBe(422);
    expect(sql(`SELECT count(*) FROM solicitud_dominio s JOIN usuario u ON u.id=s.id_solicitante WHERE u.correo='${d.correo}'`)).toBe('0');
  });
});
