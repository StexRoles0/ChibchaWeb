import { expect, test } from '@playwright/test';
import { principal, registrarCliente, VISA_RECHAZADA_VALIDADOR } from './apoyo/acciones';

test.describe('CU-CLI-03 Modificar perfil', () => {
  test('FP: las tres pestañas (PERSONAL, PAQUETE_PLAN, PAGO) guardan su bloque y el perfil lo refleja', async ({ page }) => {
    const d = await registrarCliente(page);
    await page.goto('/cliente/perfil/editar');

    // PERSONAL: el correo es de solo lectura (RN-05).
    await expect(page.getByLabel('Correo electrónico')).toHaveJSProperty('readOnly', true);
    await page.getByLabel('Teléfono').fill('3112223344');
    await page.getByLabel('Ciudad de residencia').fill('Tunja');
    let guardado = page.waitForResponse((r) => r.url().includes('/api/v1/clientes/me?categoria=PERSONAL'));
    await page.getByRole('button', { name: 'Guardar cambios' }).click();
    expect((await guardado).status()).toBe(204);
    await expect(page.getByRole('status').filter({ hasText: /guard|actualiz/i })).toBeVisible();

    // PAQUETE_PLAN
    await page.getByRole('tab', { name: 'Paquete y plan' }).click();
    await page.getByRole('radio', { name: /Chibcha-Platino/ }).check({ force: true });
    await page.getByRole('radio', { name: /Anual/ }).check({ force: true });
    guardado = page.waitForResponse((r) => r.url().includes('categoria=PAQUETE_PLAN'));
    await page.getByRole('button', { name: 'Guardar cambios' }).click();
    expect((await guardado).status()).toBe(204);

    // PAGO: exige reescribir la tarjeta completa (D-22).
    await page.getByRole('tab', { name: 'Dirección y tarjeta' }).click();
    await page.getByLabel('Dirección de facturación').fill('Av 1 # 2-3');
    await page.getByLabel('Ciudad').fill('Duitama');
    await page.getByLabel('Código postal').fill('150000');
    await page.getByLabel('Franquicia').selectOption('MASTERCARD');
    await page.getByLabel('Número de tarjeta').fill('5555555555554444');
    await page.getByLabel('Vencimiento').fill('11/31');
    await page.getByLabel('Código de seguridad').fill('321');
    guardado = page.waitForResponse((r) => r.url().includes('categoria=PAGO'));
    await page.getByRole('button', { name: 'Guardar cambios' }).click();
    expect((await guardado).status()).toBe(204);

    // Persistido: se consulta por GET /clientes/me desde M-06.
    await page.goto('/cliente/perfil');
    const perfil = principal(page);
    await expect(perfil).toContainText('3112223344');
    await expect(perfil).toContainText('Tunja');
    await expect(perfil).toContainText('Chibcha-Platino');
    await expect(perfil).toContainText('Anual');
    await expect(perfil).toContainText('•••• 4444');
    await expect(perfil).toContainText(d.correo); // el correo no cambió
  });

  test('FA: tarjeta ...0002 en la pestaña PAGO -> 422 bajo el campo y la tarjeta anterior se conserva', async ({ page }) => {
    await registrarCliente(page);
    await page.goto('/cliente/perfil/editar');
    await page.getByRole('tab', { name: 'Dirección y tarjeta' }).click();
    await page.getByLabel('Dirección de facturación').fill('Av 1 # 2-3');
    await page.getByLabel('Ciudad').fill('Duitama');
    await page.getByLabel('Código postal').fill('150000');
    await page.getByLabel('Número de tarjeta').fill(VISA_RECHAZADA_VALIDADOR);
    await page.getByLabel('Vencimiento').fill('11/31');
    await page.getByLabel('Código de seguridad').fill('321');
    const guardado = page.waitForResponse((r) => r.url().includes('categoria=PAGO'));
    await page.getByRole('button', { name: 'Guardar cambios' }).click();
    const r = await guardado;
    expect(r.status()).toBe(422);
    expect(await r.json()).toMatchObject({ codigo: 'VALIDACION', campo: 'numeroTarjeta' });
    await expect(page.locator('#numeroTarjeta-error')).toBeVisible();
    await page.goto('/cliente/perfil');
    await expect(principal(page)).toContainText('•••• 4242');
  });

  test('FA: validación en PERSONAL (teléfono vacío no se envía)', async ({ page }) => {
    await registrarCliente(page);
    await page.goto('/cliente/perfil/editar');
    await page.getByLabel('Teléfono').fill('');
    await page.getByRole('button', { name: 'Guardar cambios' }).click();
    await expect(page.locator('#telefono-error')).toBeVisible();
  });
});
