import { expect, test } from '@playwright/test';
import { cerrarSesion, crearDistribuidorApi, GESTION, ingresarComo, registrarCliente } from './apoyo/acciones';
import { hoyBogota, manage, sql, unico } from './apoyo/entorno';

function mesActual(): { inicio: string; fin: string } {
  const [a, m] = hoyBogota().split('-').map(Number);
  const ultimo = new Date(Date.UTC(a, m, 0)).getUTCDate();
  const p = String(m).padStart(2, '0');
  return { inicio: `${a}-${p}-01`, fin: `${a}-${p}-${String(ultimo).padStart(2, '0')}` };
}

// CU-COM-02 (actor Tiempo, sin pantalla): emite el cheque de cada comisión que no lo tiene.
test.describe('CU-COM-02 Generar cheque', () => {
  test('FP: genera CHQ-<año>-<id 6 dígitos> con beneficiario y monto; no repite cheques (RN-21)', async ({ page, context }) => {
    const u = unico();
    const { inicio, fin } = mesActual();
    await ingresarComo(page, GESTION, /\/gestion$/);
    const { id, codigo } = await crearDistribuidorApi(page, `chq${u}@correo.co`, `${u}09`, `Distribuidora Cheques ${u}`);
    await cerrarSesion(page);
    await context.clearCookies();
    await registrarCliente(page, { codigoDistribuidor: codigo }); // Oro semestral = 54.00
    await cerrarSesion(page);
    manage('cargar_pagos', '--fecha', hoyBogota());
    manage('calcular_comisiones', '--inicio', inicio, '--fin', fin);
    const idComision = sql(`SELECT id FROM comision WHERE id_beneficiario=${id}`);
    expect(sql(`SELECT count(*) FROM cheque WHERE id_comision=${idComision}`)).toBe('0');

    const salida = manage('generar_cheques');
    expect(salida).toMatch(/generar_cheques: \d+ cheques generados de \d+ comisiones sin cheque/);
    const anio = hoyBogota().slice(0, 4);
    // 54.00 x 10 % = 5.40; beneficiario: nombre y documento del distribuidor.
    const fila = sql(`SELECT numero, monto, beneficiario FROM cheque WHERE id_comision=${idComision}`);
    const [numero, monto, beneficiario] = fila.split('|');
    expect(numero).toBe(`CHQ-${anio}-${idComision.padStart(6, '0')}`);
    expect(monto).toBe('5.40');
    expect(beneficiario).toContain(`Distribuidora Cheques ${u}`);
    expect(beneficiario).toContain(`${u}09`);

    // Segunda ejecución: la comisión ya tiene cheque, no se emite otro.
    const otra = manage('generar_cheques');
    expect(otra).toMatch(/generar_cheques: 0 cheques generados de 0 comisiones sin cheque/);
    expect(sql(`SELECT count(*) FROM cheque WHERE id_comision=${idComision}`)).toBe('1');
  });
});
