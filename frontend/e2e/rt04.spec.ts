import { expect, test } from '@playwright/test';
import { ADMIN, ingresarComo, registrarCliente } from './apoyo/acciones';
import { dbDetener, dbIniciar, respaldarSolicitudDominio, sql, unico } from './apoyo/entorno';

// RT04: detiene y arranca el contenedor `db` del proyecto e2e. En serie y siempre deja la BD arriba.
test.describe.configure({ mode: 'serial' });
// Con la BD detenida cada petición espera ~8 s al timeout de conexión antes de responder 503 (ver informe de QA):
// los plazos de esas esperas son más largos a propósito, no hay sleeps.
const CAIDA = { timeout: 45_000 };
test.setTimeout(150_000);
test.afterEach(() => {
  dbIniciar();
});

test.describe('RT04 Contingencia', () => {
  test('BD caída: las operaciones dan 503 CONTINGENCIA con el banner, el admin sigue viendo el respaldo y al volver la BD todo funciona', async ({ browser }) => {
    const u = unico();
    const ctxCliente = await browser.newContext();
    const ctxAdmin = await browser.newContext();
    const cliente = await ctxCliente.newPage();
    const admin = await ctxAdmin.newPage();
    try {
      const d = await registrarCliente(cliente);
      await cliente.goto('/cliente/dominios');
      await expect(cliente.getByRole('heading', { name: 'Solicitar un dominio' })).toBeVisible();
      await ingresarComo(admin, ADMIN, /\/admin$/);
      await admin.goto('/admin/contingencia');
      await expect(admin.getByText('No hay eventos pendientes en el respaldo.')).toBeVisible();
      await expect(cliente.getByText('modo contingencia')).toHaveCount(0);

      dbDetener();

      // Cliente: la solicitud de dominio responde 503 CONTINGENCIA y aparece el banner global.
      await cliente.getByLabel('Nombre del dominio').fill(`caido${u}`);
      const envio = cliente.waitForResponse((r) => r.url().endsWith('/api/v1/dominios/solicitudes') && r.request().method() === 'POST', CAIDA);
      await cliente.getByRole('button', { name: 'Enviar solicitud' }).click();
      const r = await envio;
      expect(r.status()).toBe(503);
      expect((await r.json()).codigo).toBe('CONTINGENCIA');
      const banner = cliente.locator('app-banner-contingencia');
      await expect(banner).toContainText(/modo contingencia/, CAIDA);
      // La sesión sigue viva (cookie firmada, D-30): no hay redirección a M-01.
      await expect(cliente).toHaveURL(/\/cliente\/dominios$/);

      // Admin: con la BD caída consulta el respaldo (200) y cambia el algoritmo (204) sin usar la BD (D-30 (4)).
      await admin.reload();
      await expect(admin.getByRole('heading', { name: 'Contingencia de base de datos' })).toBeVisible(CAIDA);
      await admin.locator('input[value=Camellia]').check({ force: true });
      const cambio = admin.waitForResponse((x) => x.url().endsWith('/api/v1/contingencia/algoritmo'), CAIDA);
      await admin.getByRole('button', { name: 'Aplicar algoritmo' }).click();
      expect((await cambio).status()).toBe(204);
      await expect(admin.getByRole('status').filter({ hasText: /Camellia/ })).toBeVisible();

      dbIniciar();

      // Al volver la BD: se descarta el aviso y se repite la operación con éxito.
      await banner.getByRole('button', { name: 'Entendido' }).click();
      await expect(banner).toHaveCount(1);
      await expect(banner.getByText(/modo contingencia/)).toHaveCount(0);
      const reintento = cliente.waitForResponse((x) => x.url().endsWith('/api/v1/dominios/solicitudes') && x.request().method() === 'POST');
      await cliente.getByRole('button', { name: 'Enviar solicitud' }).click();
      let ok = await reintento;
      if (ok.status() === 503) {
        // La primera petición tras reiniciar el contenedor puede encontrar la conexión vieja; se registra como dato.
        test.info().annotations.push({ type: 'observación', description: 'Primer POST tras reiniciar db respondió 503 (conexión obsoleta)' });
        await banner.getByRole('button', { name: 'Entendido' }).click();
        const otra = cliente.waitForResponse((x) => x.url().endsWith('/api/v1/dominios/solicitudes') && x.request().method() === 'POST');
        await cliente.getByRole('button', { name: 'Enviar solicitud' }).click();
        ok = await otra;
      }
      expect(ok.status()).toBe(201);
      await expect(cliente.getByRole('table', { name: 'Solicitudes de dominio' }).getByRole('row', { name: new RegExp(`caido${u}`) })).toBeVisible();
      expect(sql(`SELECT count(*) FROM solicitud_dominio s JOIN usuario x ON x.id=s.id_solicitante WHERE x.correo='${d.correo}' AND s.nombre='caido${u}'`)).toBe('1');
    } finally {
      dbIniciar();
      await ctxCliente.close();
      await ctxAdmin.close();
    }
  });

  test('Sincronización: con la BD aún caída da 503 y el respaldo se conserva; al volver la BD reinserta los eventos (AES y Camellia) y lo vacía', async ({ page, browser }) => {
    const u = unico();
    // Un cliente existente y dos eventos reales en el respaldo, cifrados con algoritmos distintos (RN-29).
    const ctxCliente = await browser.newContext();
    const c = await ctxCliente.newPage();
    const d = await registrarCliente(c);
    const idCliente = Number(sql(`SELECT id FROM usuario WHERE correo='${d.correo}'`));
    respaldarSolicitudDominio(idCliente, `respaldoaes${u}`, 'AES');
    respaldarSolicitudDominio(idCliente, `respaldocam${u}`, 'Camellia');
    expect(sql(`SELECT count(*) FROM solicitud_dominio WHERE nombre LIKE 'respaldo%${u}'`)).toBe('0'); // aún no están en la BD

    await ingresarComo(page, ADMIN, /\/admin$/);
    await page.goto('/admin/contingencia');
    await expect(page.getByText('2 eventos pendientes de sincronizar.')).toBeVisible();
    const tabla = page.getByRole('table', { name: 'Eventos pendientes en el respaldo' });
    await expect(tabla.getByRole('row', { name: /Solicitud de dominio · creación.*AES/ })).toBeVisible();
    await expect(tabla.getByRole('row', { name: /Solicitud de dominio · creación.*Camellia/ })).toBeVisible();

    // Con la BD caída, Sincronizar -> 503 y el respaldo queda intacto.
    dbDetener();
    try {
      const sync = page.waitForResponse((r) => r.url().endsWith('/api/v1/contingencia/sincronizacion'), CAIDA);
      await page.getByRole('button', { name: /Sincronizar respaldo/ }).click();
      const r = await sync;
      expect(r.status()).toBe(503);
      expect((await r.json()).codigo).toBe('CONTINGENCIA');
      await expect(page.getByText('La base de datos sigue sin responder; el respaldo se conserva intacto.')).toBeVisible(CAIDA);
      await expect(page.getByText('2 eventos pendientes de sincronizar.')).toBeVisible();
    } finally {
      dbIniciar();
    }

    // La BD volvió: sincroniza todo y el respaldo queda vacío.
    await page.getByRole('button', { name: 'Entendido' }).click().catch(() => undefined);
    let intento = page.waitForResponse((x) => x.url().endsWith('/api/v1/contingencia/sincronizacion'));
    await page.getByRole('button', { name: /Sincronizar respaldo/ }).click();
    let r2 = await intento;
    if (r2.status() === 503) {
      test.info().annotations.push({ type: 'observación', description: 'Primera sincronización tras reiniciar db respondió 503 (conexión obsoleta)' });
      await page.getByRole('button', { name: 'Entendido' }).click().catch(() => undefined);
      intento = page.waitForResponse((x) => x.url().endsWith('/api/v1/contingencia/sincronizacion'));
      await page.getByRole('button', { name: /Sincronizar respaldo/ }).click();
      r2 = await intento;
    }
    expect(r2.status()).toBe(200);
    expect(await r2.json()).toEqual({ sincronizados: 2 });
    await expect(page.getByText('Se sincronizaron 2 eventos. El respaldo quedó al día.')).toBeVisible();
    await expect(page.getByText('No hay eventos pendientes en el respaldo.')).toBeVisible();

    // Persistido: las dos solicitudes están en la BD, una sola vez cada una, y el cliente las ve en M-09.
    expect(sql(`SELECT nombre, estado FROM solicitud_dominio WHERE nombre LIKE 'respaldo%${u}' ORDER BY nombre`)).toBe(`respaldoaes${u}|REGISTRADA\nrespaldocam${u}|REGISTRADA`);
    await c.goto('/cliente/dominios');
    const filas = c.getByRole('table', { name: 'Solicitudes de dominio' });
    await expect(filas.getByRole('row', { name: new RegExp(`respaldoaes${u}`) })).toBeVisible();
    await expect(filas.getByRole('row', { name: new RegExp(`respaldocam${u}`) })).toBeVisible();
    await ctxCliente.close();
  });

  test('Sin eventos pendientes el botón Sincronizar queda deshabilitado', async ({ page }) => {
    await ingresarComo(page, ADMIN, /\/admin$/);
    await page.goto('/admin/contingencia');
    await expect(page.getByRole('button', { name: /Sincronizar respaldo \(0\)/ })).toBeDisabled();
  });
});
