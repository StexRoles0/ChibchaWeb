import { expect, test } from '@playwright/test';
import { ingresar, registrarCliente } from './apoyo/acciones';
import { sql } from './apoyo/entorno';

test.describe('CU-CLI-02 Eliminar perfil', () => {
  test('FP: M-08 pide confirmación, inactiva al cliente, suspende sus suscripciones, cierra la sesión y no deja volver a entrar', async ({ page }) => {
    const d = await registrarCliente(page);
    await page.goto('/cliente/perfil/eliminar');
    const dialogo = page.getByRole('dialog', { name: 'Eliminar tu cuenta' });
    const confirmar = dialogo.getByRole('button', { name: 'Eliminar mi cuenta' });
    // Hasta escribir el correo no se habilita el botón peligroso.
    await expect(confirmar).toBeDisabled();
    await dialogo.getByLabel('Escribe tu correo para confirmar').fill(d.correo);
    await expect(confirmar).toBeEnabled();
    const baja = page.waitForResponse((r) => r.url().endsWith('/api/v1/clientes/me') && r.request().method() === 'DELETE');
    await confirmar.click();
    expect((await baja).status()).toBe(204);
    await expect(page).toHaveURL(/\/acceso$/);
    expect((await page.request.get('/api/v1/auth/sesion')).status()).toBe(401);

    // Persistido: baja lógica (RN-09) y suscripciones suspendidas.
    expect(sql(`SELECT activo FROM usuario WHERE correo='${d.correo}'`)).toBe('f');
    expect(sql(`SELECT s.activa FROM suscripcion s JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${d.correo}'`)).toBe('f');
    // Y por la interfaz: no puede iniciar sesión.
    const callback = page.waitForResponse((r) => r.url().includes('/api/v1/auth/oauth/callback'));
    await ingresar(page, d.correo);
    const r = await callback;
    expect(r.status()).toBe(403);
    expect((await r.json()).codigo).toBe('USUARIO_INACTIVO');
    await expect(page).toHaveURL(/\/acceso$/);
  });

  test('FA: Cancelar el diálogo no elimina nada', async ({ page }) => {
    const d = await registrarCliente(page);
    await page.goto('/cliente/perfil/eliminar');
    const dialogo = page.getByRole('dialog', { name: 'Eliminar tu cuenta' });
    await dialogo.getByRole('button', { name: 'Cancelar' }).click();
    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(page).toHaveURL(/\/cliente\/perfil$/);
    expect(sql(`SELECT activo FROM usuario WHERE correo='${d.correo}'`)).toBe('t');
  });
});
