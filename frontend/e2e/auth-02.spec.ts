import { expect, test } from '@playwright/test';
import { ADMIN, cabecerasApi, cerrarSesion, crearEmpleadoApi, GESTION, ingresar, menu, ingresarComo, registrarCliente, SOPORTE } from './apoyo/acciones';
import { sql, unico } from './apoyo/entorno';

test.describe('CU-AUTH-02 Iniciar sesión', () => {
  test('FP: cada rol aterriza en su inicio (Gestión, Soporte, Administrador y Cliente)', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    await expect(menu(page).getByRole('link', { name: 'Empleados' })).toBeVisible();
    await cerrarSesion(page);

    await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
    await expect(page.getByRole('heading', { name: 'Tickets del día' })).toBeVisible();
    await cerrarSesion(page);

    await ingresarComo(page, ADMIN, /\/admin$/);
    await expect(menu(page).getByRole('link', { name: 'Migración' })).toBeVisible();
    await cerrarSesion(page);

    const cliente = await registrarCliente(page);
    await cerrarSesion(page);
    await ingresarComo(page, cliente.correo, /\/cliente$/);
    await expect(page.getByRole('heading', { name: /^Hola/ })).toBeVisible();
    // La sesión queda abierta: GET /auth/sesion responde con el resultado del acceso.
    const sesion = await page.request.get('/api/v1/auth/sesion');
    expect(sesion.status()).toBe(200);
    expect(await sesion.json()).toMatchObject({ registrado: true, tipoUsuario: 'CLIENTE', correo: cliente.correo });
  });

  test('FA1 (RN-07): un empleado sin cuenta vincula su identidad por correo verificado y reingresa por sub', async ({ page }) => {
    const correo = `empleado${unico()}@chibchaweb.co`;
    await ingresarComo(page, GESTION, /\/gestion$/);
    await crearEmpleadoApi(page, correo, `D-${unico()}`);
    expect(sql(`SELECT count(*) FROM cuenta_acceso c JOIN usuario u ON u.id=c.id_titular WHERE u.correo='${correo}'`)).toBe('0');
    await cerrarSesion(page);

    await ingresarComo(page, correo, /\/(gestion|soporte\/bandeja|admin)$/); // primer ingreso: vincula por correo
    expect(sql(`SELECT c.identificador_externo FROM cuenta_acceso c JOIN usuario u ON u.id=c.id_titular WHERE u.correo='${correo}'`)).toBe(`dev|${correo}`);
    await cerrarSesion(page);
    await ingresar(page, correo); // segundo ingreso: se encuentra por sub, no vincula otra vez
    await expect(page).toHaveURL(/\/(gestion|soporte\/bandeja|admin)$/);
    expect(sql(`SELECT count(*) FROM cuenta_acceso c JOIN usuario u ON u.id=c.id_titular WHERE u.correo='${correo}'`)).toBe('1');
  });

  test('FA2: un correo desconocido va a M-02 con nombre y correo verificados', async ({ page }) => {
    const correo = `visitante${unico()}@correo.co`;
    await ingresar(page, correo);
    await expect(page).toHaveURL(/\/registro\/datos$/);
    await expect(page.getByLabel('Correo electrónico')).toHaveValue(correo);
    await expect(page.getByLabel('Correo electrónico')).toHaveJSProperty('readOnly', true);
    await expect(page.getByText('✓ Verificado')).toBeVisible();
    await expect(page.getByLabel('Nombre completo')).not.toHaveValue('');
  });

  test('FA3a: usuario inactivo -> 403 USUARIO_INACTIVO y mensaje en M-01', async ({ page }) => {
    const correo = `baja${unico()}@chibchaweb.co`;
    await ingresarComo(page, GESTION, /\/gestion$/);
    const id = await crearEmpleadoApi(page, correo, `D-${unico()}`);
    const baja = await page.request.delete(`/api/v1/empleados/${id}`, { headers: await cabecerasApi(page) });
    expect(baja.status()).toBe(204);
    await cerrarSesion(page);

    const callback = page.waitForResponse((r) => r.url().includes('/api/v1/auth/oauth/callback'));
    await ingresar(page, correo);
    const r = await callback;
    expect(r.status()).toBe(403);
    expect((await r.json()).codigo).toBe('USUARIO_INACTIVO');
    await expect(page).toHaveURL(/\/acceso$/);
    await expect(page.getByRole('alert').filter({ hasText: /baja|inactiv/i })).toBeVisible();
  });

  test('FA3b: código inválido o state distinto -> 401 AUTORIZACION_FALLIDA y mensaje en M-01', async ({ page }) => {
    await page.goto('/auth/callback?code=dev:alguien@correo.co&state=estado-que-no-corresponde');
    await expect(page).toHaveURL(/\/acceso$/);
    await expect(page.getByRole('alert').filter({ hasText: /acceso|autoriz/i })).toBeVisible();
    const sesion = await page.request.get('/api/v1/auth/sesion');
    expect(sesion.status()).toBe(401); // no quedó ninguna sesión abierta
  });
});
