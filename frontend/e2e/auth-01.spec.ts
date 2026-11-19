import { expect, test } from '@playwright/test';
import { ADMIN, cerrarSesion, GESTION, ingresarComo, SOPORTE } from './apoyo/acciones';

test.describe('CU-AUTH-01 Acceder', () => {
  test('FP: M-01 ofrece iniciar sesión y crear cuenta, y ambas piden GET /auth/oauth/inicio', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/acceso$/);
    await expect(page.getByRole('heading', { name: 'Bienvenido' })).toBeVisible();
    const iniciar = page.getByRole('button', { name: /Iniciar sesión con proveedor/ });
    const crear = page.getByRole('button', { name: 'Crear una cuenta' });
    await expect(iniciar).toBeVisible();
    await expect(crear).toBeVisible();

    for (const boton of [iniciar, crear]) {
      await page.goto('/acceso');
      await page.getByLabel(/Correo de prueba/).fill('nuevo.visitante@correo.co');
      const inicio = page.waitForResponse((r) => r.url().includes('/api/v1/auth/oauth/inicio'));
      const callback = page.waitForRequest((r) => r.url().includes('/api/v1/auth/oauth/callback'));
      await boton.click();
      expect((await inicio).status()).toBe(200);
      // La URL que devolvió /inicio redirige a /auth/callback con el código del proveedor simulado.
      expect((await callback).postDataJSON().codigo).toBe('dev:nuevo.visitante@correo.co');
      // Con el proveedor simulado la redirección vuelve al callback y, sin cuenta, lleva al registro.
      await expect(page).toHaveURL(/\/registro\/datos$/);
      await page.getByRole('button', { name: 'Volver' }).click(); // cancelar registro: cierra la sesión pendiente
      await expect(page).toHaveURL(/\/acceso$/);
    }
  });

  test('FP: sin el correo de prueba no se puede salir hacia el proveedor', async ({ page }) => {
    await page.goto('/acceso');
    await page.getByRole('button', { name: /Iniciar sesión con proveedor/ }).click();
    await expect(page.getByText('Escribe un correo de prueba válido para continuar.')).toBeVisible();
    await expect(page).toHaveURL(/\/acceso$/);
  });

  test('FA: con sesión válida /acceso va directo al inicio del rol', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto('/acceso');
    await expect(page).toHaveURL(/\/gestion$/);

    await cerrarSesion(page);
    await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
    await page.goto('/acceso');
    await expect(page).toHaveURL(/\/soporte\/bandeja$/);

    await cerrarSesion(page);
    await ingresarComo(page, ADMIN, /\/admin$/);
    await page.goto('/acceso');
    await expect(page).toHaveURL(/\/admin$/);
  });

  test('FA: una ruta protegida sin sesión manda a M-01 (401)', async ({ page }) => {
    await page.goto('/gestion/empleados');
    await expect(page).toHaveURL(/\/acceso$/);
  });
});
