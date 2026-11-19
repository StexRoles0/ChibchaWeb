import { expect, test } from '@playwright/test';
import { ingresarComo, menu, principal, registrarCliente, cerrarSesion } from './apoyo/acciones';

test.describe('CU-CLI-01 Gestionar perfil', () => {
  test('FP: M-06 muestra datos personales, sitio, paquete y plan, dirección y tarjeta enmascarada, con Modificar y Eliminar', async ({ page }) => {
    const d = await registrarCliente(page, { paquete: 'Chibcha-Platino', plan: 'Anual' });
    await cerrarSesion(page);
    await ingresarComo(page, d.correo, /\/cliente$/);

    const detalle = page.waitForResponse((r) => r.url().endsWith('/api/v1/clientes/me'));
    await menu(page).getByRole('link', { name: 'Mi perfil' }).click();
    expect((await detalle).status()).toBe(200);
    await expect(page).toHaveURL(/\/cliente\/perfil$/);
    const perfil = principal(page);
    await expect(perfil.getByRole('heading', { name: 'Mi perfil' })).toBeVisible();
    for (const texto of [d.nombre, d.correo, d.telefono, 'Calle 10 # 5-20, Sogamoso', 'Sin distribuidor', `${d.sitio}.chibchaweb.`, 'Windows', 'Chibcha-Platino', 'Anual', 'VISA •••• 4242', '12/30']) {
      await expect(perfil).toContainText(texto);
    }
    await expect(perfil).not.toContainText(d.tarjeta);
    await expect(perfil.getByRole('link', { name: /Modificar perfil/ })).toBeVisible();
    await expect(perfil.getByRole('link', { name: /Eliminar perfil/ })).toBeVisible();
  });
});
