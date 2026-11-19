import { expect, test } from '@playwright/test';
import { cerrarSesion, crearDistribuidorApi, GESTION, ingresarComo, registrarCliente, VISA_COBRO_FALLIDO } from './apoyo/acciones';
import { hoyBogota, manage, sql, unico } from './apoyo/entorno';

/** Primer y último día del mes en curso (Bogotá). */
function mesActual(): { inicio: string; fin: string } {
  const [a, m] = hoyBogota().split('-').map(Number);
  const ultimo = new Date(Date.UTC(a, m, 0)).getUTCDate();
  const p = String(m).padStart(2, '0');
  return { inicio: `${a}-${p}-01`, fin: `${a}-${p}-${String(ultimo).padStart(2, '0')}` };
}

// CU-COM-01 (actor Tiempo, sin pantalla). Se usa un distribuidor propio para aislar sus cifras de las demás pruebas.
test.describe('CU-COM-01 Calcular comisión', () => {
  test('FP: crea una comisión Básica (10 %) con solo los pagos EXITOSO de sus referidos; correr de nuevo no duplica', async ({ page, context }) => {
    const u = unico();
    const { inicio, fin } = mesActual();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id, codigo } = await crearDistribuidorApi(page, `com${u}@correo.co`, `${u}07`, `Distribuidora Comisiones ${u}`);
    await cerrarSesion(page);
    await context.clearCookies();

    // Dos referidos: uno paga 54.00 (Oro semestral) y otro tiene la tarjeta ...0341 (cobro fallido).
    const a = await registrarCliente(page, { codigoDistribuidor: codigo });
    await cerrarSesion(page);
    await context.clearCookies();
    const b = await registrarCliente(page, { codigoDistribuidor: codigo, tarjeta: VISA_COBRO_FALLIDO });
    await cerrarSesion(page);
    manage('cargar_pagos', '--fecha', hoyBogota());
    expect(sql(`SELECT p.estado FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${a.correo}'`)).toBe('EXITOSO');
    expect(sql(`SELECT p.estado FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${b.correo}'`)).toBe('FALLIDO');

    const salida = manage('calcular_comisiones', '--inicio', inicio, '--fin', fin);
    expect(salida).toMatch(new RegExp(`calcular_comisiones ${inicio} a ${fin}: \\d+ comisiones creadas`));
    // RN-19/20: categoría Básica (2 referidos <= 100), 10 %, y solo el pago EXITOSO queda comisionado.
    expect(sql(`SELECT count(*), max(nombre_categoria), max(porcentaje), max(clientes_referidos) FROM comision WHERE id_beneficiario=${id}`)).toMatch(/^1\|Básic[ao]\|0\.10\|2$/);
    expect(sql(`SELECT p.estado, p.comisionado, p.id_comision IS NOT NULL FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${a.correo}'`)).toBe('EXITOSO|t|t');
    expect(sql(`SELECT p.estado, p.comisionado FROM pago p JOIN suscripcion s ON s.id=p.id_suscripcion JOIN usuario u ON u.id=s.id_titular WHERE u.correo='${b.correo}'`)).toBe('FALLIDO|f');

    // Idempotencia: el mismo periodo otra vez no duplica (los pagos ya están comisionados).
    manage('calcular_comisiones', '--inicio', inicio, '--fin', fin);
    expect(sql(`SELECT count(*) FROM comision WHERE id_beneficiario=${id}`)).toBe('1');

    // Visible por la interfaz de Gestión: el distribuidor tiene 2 referidos.
    await ingresarComo(page, GESTION, /\/gestion$/);
    await page.goto(`/gestion/distribuidores/${id}`);
    await expect(page.getByRole('heading', { name: 'Código y comisión' })).toBeVisible();
    await expect(page.locator('dt', { hasText: 'Referidos' }).locator('xpath=following-sibling::dd[1]')).toHaveText('2');
  });

  test('FA: un distribuidor sin pagos no recibe comisión', async ({ page }) => {
    const u = unico();
    const { inicio, fin } = mesActual();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id } = await crearDistribuidorApi(page, `sinpagos${u}@correo.co`, `${u}08`, `Distribuidora Sin Pagos ${u}`);
    manage('calcular_comisiones', '--inicio', inicio, '--fin', fin);
    expect(sql(`SELECT count(*) FROM comision WHERE id_beneficiario=${id}`)).toBe('0');
  });

  test('FA: --inicio sin --fin es un error del comando', async () => {
    expect(() => manage('calcular_comisiones', '--inicio', '2026-01-01')).toThrow(/--inicio y --fin juntos/);
  });
});
