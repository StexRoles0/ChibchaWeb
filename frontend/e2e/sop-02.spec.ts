import { expect, test } from '@playwright/test';
import { cabecerasApi, cerrarSesion, crearTicketApi, GESTION, ingresarComo, SOPORTE } from './apoyo/acciones';
import { hoyBogota, unico } from './apoyo/entorno';

function ayer(): string {
  const [a, m, d] = hoyBogota().split('-').map(Number);
  return new Date(Date.UTC(a, m - 1, d - 1)).toISOString().slice(0, 10);
}

test.describe('CU-SOP-02 Consultar tickets diario', () => {
  test('FP + RN-24: la bandeja del día muestra los creados hoy y los abiertos de otros días, sin los resueltos de otro día', async ({ page }) => {
    const u = unico();
    // Preparación: dos tickets de hoy; el segundo se resuelve.
    await ingresarComo(page, GESTION, /\/gestion$/);
    const abierto = await crearTicketApi(page, 'OTRA', `Abierto ${u}`);
    const resuelto = await crearTicketApi(page, 'CORREO', `A resolver ${u}`);
    await cerrarSesion(page);

    await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
    const r = await page.request.post(`/api/v1/tickets/${resuelto}/enrutamiento`, {
      headers: await cabecerasApi(page),
      data: { escalar: false, observacion: 'Resuelto en la preparación' },
    });
    expect(r.status()).toBe(204);

    // Hoy (por defecto): aparecen ambos, con su estado.
    await page.goto('/soporte/bandeja');
    const tabla = page.getByRole('table', { name: 'Tickets del día' });
    await expect(page.getByLabel('Fecha')).toHaveValue(hoyBogota());
    await expect(tabla.getByRole('row', { name: new RegExp(`#${abierto}\\b`) })).toContainText(/abierto/i);
    await expect(tabla.getByRole('row', { name: new RegExp(`#${resuelto}\\b`) })).toContainText(/resuelto/i);

    // Ayer: solo siguen los abiertos/escalados; el resuelto de hoy no.
    const diario = page.waitForResponse((x) => x.url().includes(`/api/v1/tickets/diarios?fecha=${ayer()}`));
    await page.getByLabel('Fecha').fill(ayer());
    expect((await diario).status()).toBe(200);
    await expect(tabla.getByRole('row', { name: new RegExp(`#${abierto}\\b`) })).toBeVisible();
    await expect(tabla.getByRole('row', { name: new RegExp(`#${resuelto}\\b`) })).toHaveCount(0);
  });

  test('FA: la bandeja va del más reciente al más antiguo y una fecha antigua responde 200', async ({ page }) => {
    await ingresarComo(page, SOPORTE, /\/soporte\/bandeja$/);
    const ids = await page.locator('tbody a.num').allInnerTexts();
    const numeros = ids.map((t) => Number(t.match(/#(\d+)/)![1]));
    expect(numeros).toEqual([...numeros].sort((a, b) => b - a));
    const r = await page.request.get('/api/v1/tickets/diarios?fecha=2000-01-01');
    expect(r.status()).toBe(200);
  });

  test('FA (permiso): Gestión recibe 403 SIN_PERMISO en la bandeja', async ({ page }) => {
    await ingresarComo(page, GESTION, /\/gestion$/);
    const r = await page.request.get('/api/v1/tickets/diarios');
    expect(r.status()).toBe(403);
    expect((await r.json()).codigo).toBe('SIN_PERMISO');
    await page.goto('/soporte/bandeja');
    await expect(page).toHaveURL(/\/no-autorizado$/);
  });
});
