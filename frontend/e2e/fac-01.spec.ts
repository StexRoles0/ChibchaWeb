import { expect, test } from '@playwright/test';
import { cerrarSesion, ingresarComo, registrarCliente, VISA_COBRO_FALLIDO } from './apoyo/acciones';
import { fechaCortaUi, hoyBogota, manage, sql, sumarMeses } from './apoyo/entorno';

// CU-FAC-01 (actor Tiempo, sin pantalla): se ejecuta el comando y se verifica el efecto por la interfaz y la BD.
test.describe('CU-FAC-01 Cargar pago', () => {
  test('FP + FA: cobra las suscripciones vencidas; la tarjeta ...0341 queda FALLIDO sin mover el corte y no frena el lote', async ({ page, context }) => {
    const hoy = hoyBogota();
    const bueno = await registrarCliente(page, { plan: 'Trimestral' });
    await cerrarSesion(page);
    await context.clearCookies();
    const malo = await registrarCliente(page, { plan: 'Trimestral', tarjeta: VISA_COBRO_FALLIDO });
    await cerrarSesion(page);

    // RN-04: ambas nacen con fechaCorte = hoy (vencidas, RN-02).
    for (const c of [bueno, malo]) {
      expect(sql(`SELECT s.fecha_corte FROM suscripcion s JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${c.correo}'`)).toBe(hoy);
    }

    const salida = manage('cargar_pagos', '--fecha', hoy);
    expect(salida).toMatch(/cargar_pagos \d{4}-\d{2}-\d{2}: \d+ cobros procesados/);
    expect(Number(/: (\d+) cobros/.exec(salida)![1])).toBeGreaterThanOrEqual(2);

    // Cobro exitoso: pago EXITOSO con referencia REF-xxxxxxxx por 10 x 3 x 0.95 = 28.50 y corte + 3 meses.
    expect(sql(`SELECT p.estado, p.monto, p.referencia_franquicia ~ '^REF-' FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${bueno.correo}'`)).toBe('EXITOSO|28.50|t');
    const nuevoCorte = sumarMeses(hoy, 3);
    expect(sql(`SELECT s.fecha_corte FROM suscripcion s JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${bueno.correo}'`)).toBe(nuevoCorte);
    // ...visible en la interfaz del cliente (M-05 "Próximo cobro").
    await ingresarComo(page, bueno.correo, /\/cliente$/);
    await expect(page.getByRole('article').filter({ hasText: 'Próximo cobro' })).toContainText(fechaCortaUi(nuevoCorte));
    await cerrarSesion(page);

    // Cobro fallido (RN-03): pago FALLIDO sin referencia, el corte no se mueve.
    expect(sql(`SELECT p.estado, p.referencia_franquicia IS NULL FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${malo.correo}'`)).toBe('FALLIDO|t');
    expect(sql(`SELECT s.fecha_corte FROM suscripcion s JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${malo.correo}'`)).toBe(hoy);
    await ingresarComo(page, malo.correo, /\/cliente$/);
    await expect(page.getByRole('article').filter({ hasText: 'Próximo cobro' })).toContainText(fechaCortaUi(hoy));
  });

  test('FA: volver a correr el comando el mismo día no cobra otra vez a quien ya pagó', async ({ page }) => {
    const hoy = hoyBogota();
    const c = await registrarCliente(page);
    await cerrarSesion(page);
    manage('cargar_pagos', '--fecha', hoy);
    const antes = sql(`SELECT count(*) FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${c.correo}'`);
    expect(antes).toBe('1');
    manage('cargar_pagos', '--fecha', hoy);
    expect(sql(`SELECT count(*) FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${c.correo}'`)).toBe('1');
  });

  test('FA: una suscripción de un cliente dado de baja (suspendida) no se cobra', async ({ page }) => {
    const hoy = hoyBogota();
    const c = await registrarCliente(page);
    await page.goto('/cliente/perfil/eliminar');
    await page.getByRole('dialog').getByLabel('Escribe tu correo para confirmar').fill(c.correo);
    await page.getByRole('dialog').getByRole('button', { name: 'Eliminar mi cuenta' }).click();
    await expect(page).toHaveURL(/\/acceso$/);
    manage('cargar_pagos', '--fecha', hoy);
    expect(sql(`SELECT count(*) FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${c.correo}'`)).toBe('0');
  });
});
