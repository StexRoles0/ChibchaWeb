import { expect, test } from '@playwright/test';
import { cabecerasApi, cerrarSesion, crearTicketApi, GESTION, ingresarComo, SOPORTE } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

async function ticketNuevo(page: import('@playwright/test').Page, descripcion: string): Promise<number> {
  await ingresarComo(page, GESTION, /\/gestion$/);
  const id = await crearTicketApi(page, 'BASE_DATOS', descripcion);
  await cerrarSesion(page);
  await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
  return id;
}

test.describe('CU-SOP-03 Enrutar por nivel de servicio', () => {
  test('FP: escalar Soporte -> Gestión -> Desarrollo (último), movimientos con observación, y luego marcar resuelto', async ({ page }) => {
    const u = unico();
    const id = await ticketNuevo(page, `Base de datos caída ${u}`);
    await page.goto(`/soporte/tickets/${id}`);
    const detalle = page.getByLabel('Detalle del ticket');
    const observacion = detalle.getByLabel('Observación');

    // Observación obligatoria (422 / ayuda del formulario).
    await detalle.getByRole('button', { name: 'Escalar a Gestión' }).click();
    await expect(page.locator('#observacion-error')).toBeVisible();

    await observacion.fill('Escalo a gestión');
    let enrutar = page.waitForResponse((r) => r.url().endsWith(`/api/v1/tickets/${id}/enrutamiento`));
    await detalle.getByRole('button', { name: 'Escalar a Gestión' }).click();
    expect((await enrutar).status()).toBe(204);
    await expect(detalle).toContainText('ESCALADO');

    await observacion.fill('Escalo a desarrollo');
    enrutar = page.waitForResponse((r) => r.url().endsWith(`/api/v1/tickets/${id}/enrutamiento`));
    await detalle.getByRole('button', { name: 'Escalar a Desarrollo' }).click();
    expect((await enrutar).status()).toBe(204);

    // Último nivel: ya no se puede escalar y la interfaz lo explica.
    await expect(detalle.getByRole('button', { name: /Escalar/ })).toBeDisabled();
    await expect(detalle.getByText(/último nivel de servicio/)).toBeVisible();

    await observacion.fill('Resuelto por desarrollo');
    enrutar = page.waitForResponse((r) => r.url().endsWith(`/api/v1/tickets/${id}/enrutamiento`));
    await detalle.getByRole('button', { name: 'Marcar resuelto' }).click();
    expect((await enrutar).status()).toBe(204);
    await expect(detalle.getByText('Este ticket ya está resuelto; no admite más cambios de nivel.')).toBeVisible();

    // Persistido: se recarga el detalle (GET /tickets/{id}) con los tres movimientos en orden.
    await page.reload();
    const movimientos = page.getByLabel('Detalle del ticket').locator('.movimientos li');
    await expect(movimientos).toHaveCount(3);
    await expect(movimientos.nth(0)).toContainText('Escalo a gestión');
    await expect(movimientos.nth(1)).toContainText('Escalo a desarrollo');
    await expect(movimientos.nth(2)).toContainText('Resuelto por desarrollo');
    expect(sql(`SELECT t.estado, n.nombre FROM ticket t JOIN nivel_servicio n ON n.id=t.id_nivel_actual WHERE t.id=${id}`)).toBe('RESUELTO|Desarrollo');
    expect(sql(`SELECT count(*) FROM movimiento_ticket WHERE id_ticket=${id}`)).toBe('3');
  });

  test('FA: escalar en el último nivel -> 409 ESTADO_INVALIDO (pantalla desactualizada que aún ofrece Escalar)', async ({ browser }) => {
    const u = unico();
    const contexto = await browser.newContext();
    const a = await contexto.newPage();
    const id = await ticketNuevo(a, `Ticket de carrera ${u}`);
    await a.goto(`/soporte/tickets/${id}`);
    const detalleA = a.getByLabel('Detalle del ticket');
    await detalleA.getByLabel('Observación').fill('Primer escalado');
    await detalleA.getByRole('button', { name: 'Escalar a Gestión' }).click();
    await expect(detalleA).toContainText('ESCALADO');
    // A queda mostrando "Escalar a Desarrollo" habilitado.
    const escalarA = detalleA.getByRole('button', { name: 'Escalar a Desarrollo' });
    await expect(escalarA).toBeEnabled();

    // Otra persona de Soporte (misma cuenta, otra pestaña) lo lleva al último nivel.
    const b = await contexto.newPage();
    const r = await b.request.post(`/api/v1/tickets/${id}/enrutamiento`, { headers: await cabecerasApi(a), data: { escalar: true, observacion: 'Escalado desde otra pestaña' } });
    expect(r.status()).toBe(204);

    await detalleA.getByLabel('Observación').fill('Intento en el último nivel');
    const intento = a.waitForResponse((x) => x.url().endsWith(`/api/v1/tickets/${id}/enrutamiento`));
    await escalarA.click();
    const respuesta = await intento;
    expect(respuesta.status()).toBe(409);
    expect((await respuesta.json()).codigo).toBe('ESTADO_INVALIDO');
    await expect(detalleA.getByRole('alert')).toBeVisible();
    // No se creó ningún movimiento extra: 2 (el de A y el de B).
    expect(sql(`SELECT count(*) FROM movimiento_ticket WHERE id_ticket=${id}`)).toBe('2');
    await contexto.close();
  });

  test('FA: enrutar un ticket ya RESUELTO -> 409 ESTADO_INVALIDO; sin observación -> 422', async ({ page }) => {
    const u = unico();
    const id = await ticketNuevo(page, `Ticket resuelto ${u}`);
    const url = `/api/v1/tickets/${id}/enrutamiento`;
    const sinObs = await page.request.post(url, { headers: await cabecerasApi(page), data: { escalar: false, observacion: '' } });
    expect(sinObs.status()).toBe(422);
    expect((await sinObs.json()).codigo).toBe('VALIDACION');
    const ok = await page.request.post(url, { headers: await cabecerasApi(page), data: { escalar: false, observacion: 'Listo' } });
    expect(ok.status()).toBe(204);
    for (const escalar of [true, false]) {
      const r = await page.request.post(url, { headers: await cabecerasApi(page), data: { escalar, observacion: 'Otra vez' } });
      expect(r.status()).toBe(409);
      expect((await r.json()).codigo).toBe('ESTADO_INVALIDO');
    }
  });
});
