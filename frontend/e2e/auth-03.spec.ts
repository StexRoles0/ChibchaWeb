import { expect, test } from '@playwright/test';
import {
  datosRegistro, ingresar, llenarPaso1, llenarPaso2, llenarPaso3, principal, registrarCliente, VISA_RECHAZADA_VALIDADOR,
} from './apoyo/acciones';
import { hoyBogota, sql } from './apoyo/entorno';

test.describe('CU-AUTH-03 Registrarse', () => {
  test('FP: M-02 -> M-03 (monto en vivo) -> M-04 -> Crear cuenta -> M-05, con distribuidor y datos persistidos', async ({ page }) => {
    const d = datosRegistro({ codigoDistribuidor: 'DIS-ANDES1' });
    await ingresar(page, d.correo);
    await expect(page).toHaveURL(/\/registro\/datos$/);
    await llenarPaso1(page, d);

    // M-03: la vista previa usa RN-01 (Oro 10 x 6 meses, -10 % = 54.00).
    await expect(page).toHaveURL(/\/registro\/plan$/);
    await page.getByRole('radio', { name: /Chibcha-Oro/ }).check({ force: true });
    await page.getByRole('radio', { name: /Semestral/ }).check({ force: true });
    const resumen = page.getByRole('region', { name: 'Resumen del monto' });
    await expect(resumen).toContainText('Total por periodo');
    await expect(resumen).toContainText('54.00');
    await page.getByRole('button', { name: 'Continuar' }).click();

    // M-04: la franquicia se detecta al escribir el número.
    await expect(page).toHaveURL(/\/registro\/pago$/);
    await page.getByLabel('Número de tarjeta').fill(d.tarjeta);
    await expect(page.getByLabel('Franquicia')).toHaveValue('VISA');
    await page.getByLabel('Vencimiento').fill('12/30');
    await page.getByLabel('Código de seguridad').fill('123');
    await expect(page.getByLabel('Código de seguridad')).toHaveAttribute('type', 'password');
    const registro = page.waitForResponse((r) => r.url().endsWith('/api/v1/auth/registro'));
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    expect((await registro).status()).toBe(201);
    await expect(page).toHaveURL(/\/cliente$/);

    // Persistido y visible por otro endpoint (GET /clientes/me) en M-06.
    await page.goto('/cliente/perfil');
    const perfil = principal(page);
    await expect(perfil).toContainText(d.correo);
    await expect(perfil).toContainText(new RegExp(`${d.sitio}\\.chibchaweb\\.`));
    await expect(perfil).toContainText('Chibcha-Oro');
    await expect(perfil).toContainText('Semestral');
    await expect(perfil).toContainText('DIS-ANDES1');
    await expect(perfil).toContainText('4242');
    await expect(perfil).not.toContainText(d.tarjeta);
    // RN-04: suscripción con fechaInicio = fechaCorte = hoy.
    expect(
      sql(`SELECT s.fecha_inicio, s.fecha_corte FROM suscripcion s JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${d.correo}'`),
    ).toBe(`${hoyBogota()}|${hoyBogota()}`);
  });

  test('FA: tarjeta ...0002 rechazada por el validador -> 422 bajo el campo y no se crea nada; con otra tarjeta se completa', async ({ page }) => {
    const d = datosRegistro({ tarjeta: VISA_RECHAZADA_VALIDADOR });
    await ingresar(page, d.correo);
    await llenarPaso1(page, d);
    await llenarPaso2(page, d);
    await expect(page).toHaveURL(/\/registro\/pago$/);
    await page.getByLabel('Número de tarjeta').fill(d.tarjeta);
    await page.getByLabel('Vencimiento').fill('12/30');
    await page.getByLabel('Código de seguridad').fill('123');
    const registro = page.waitForResponse((r) => r.url().endsWith('/api/v1/auth/registro'));
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    const r = await registro;
    expect(r.status()).toBe(422);
    expect(await r.json()).toMatchObject({ codigo: 'VALIDACION', campo: 'numeroTarjeta' });
    await expect(page).toHaveURL(/\/registro\/pago$/);
    await expect(page.locator('#numeroTarjeta-error')).toBeVisible();
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='${d.correo}'`)).toBe('0');

    // Corregir la tarjeta y reintentar: el registro se completa con los datos de los pasos anteriores.
    await page.getByLabel('Número de tarjeta').fill('4242424242424242');
    await page.getByLabel('Código de seguridad').fill('123');
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    await expect(page).toHaveURL(/\/cliente$/);
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='${d.correo}'`)).toBe('1');
  });

  test('FA: subdominio ocupado -> 409 SUBDOMINIO_EN_USO y no se crea la segunda cuenta', async ({ page, context }) => {
    const primero = await registrarCliente(page);
    await page.getByRole('button', { name: 'Cerrar sesión' }).click();
    await expect(page).toHaveURL(/\/acceso$/);
    await context.clearCookies();

    const d = datosRegistro({ sitio: primero.sitio });
    await ingresar(page, d.correo);
    await llenarPaso1(page, d);
    await llenarPaso2(page, d);
    await expect(page).toHaveURL(/\/registro\/pago$/);
    await page.getByLabel('Número de tarjeta').fill(d.tarjeta);
    await page.getByLabel('Vencimiento').fill('12/30');
    await page.getByLabel('Código de seguridad').fill('123');
    const registro = page.waitForResponse((r) => r.url().endsWith('/api/v1/auth/registro'));
    await page.getByRole('button', { name: 'Crear cuenta' }).click();
    const r = await registro;
    expect(r.status()).toBe(409);
    expect((await r.json()).codigo).toBe('SUBDOMINIO_EN_USO');
    await expect(page).toHaveURL(/\/registro\/datos$/); // el frontend vuelve al paso del campo `sitio`
    await expect(page.locator('#sitio-error')).toBeVisible();
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='${d.correo}'`)).toBe('0');
  });

  test('FA: código de distribuidor inexistente -> 422 y el frontend vuelve al paso 1 con el error en ese campo', async ({ page }) => {
    const d = datosRegistro({ codigoDistribuidor: 'DIS-NOEXIS' });
    await ingresar(page, d.correo);
    await llenarPaso1(page, d);
    await llenarPaso2(page, d);
    await llenarPaso3(page, d);
    await expect(page).toHaveURL(/\/registro\/datos$/);
    await expect(page.locator('#codigoDistribuidor-error')).toBeVisible();
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='${d.correo}'`)).toBe('0');
  });

  test('FA: Cancelar (Volver en el paso 1) borra la identidad pendiente y vuelve a M-01', async ({ page }) => {
    const d = datosRegistro();
    await ingresar(page, d.correo);
    await expect(page).toHaveURL(/\/registro\/datos$/);
    await page.getByRole('button', { name: 'Volver' }).click();
    await expect(page).toHaveURL(/\/acceso$/);
    await page.goto('/registro/datos');
    await expect(page).toHaveURL(/\/acceso$/); // la guarda identidadPendiente ya no deja pasar
    expect((await page.request.get('/api/v1/auth/sesion')).status()).toBe(401);
    expect(sql(`SELECT count(*) FROM usuario WHERE correo='${d.correo}'`)).toBe('0');
  });
});
