import { aPaquete, aPlan } from './catalogo';
import {
  calcularMonto,
  centavosADecimal,
  decimalACentavos,
  descuentoAPuntosBasicos,
  MontoPipe,
} from './monto';
import { aMontoTexto } from './resumen-monto';

describe('monto (RN-01, aritmética en centavos)', () => {
  it('convierte decimales a centavos y de vuelta sin float', () => {
    expect(decimalACentavos('20.00')).toBe(2000);
    expect(decimalACentavos('5')).toBe(500);
    expect(decimalACentavos('0.1')).toBe(10);
    expect(decimalACentavos('abc')).toBeNaN();
    expect(centavosADecimal(5400)).toBe('54.00');
    expect(centavosADecimal(5)).toBe('0.05');
    expect(descuentoAPuntosBasicos('0.15')).toBe(1500);
    expect(descuentoAPuntosBasicos('0.05')).toBe(500);
  });

  it('Oro + Semestral = 54.00 (ejemplo de reglas-negocio.md)', () => {
    expect(calcularMonto(1000, 6, 1000).totalCentavos).toBe(5400);
  });

  it('Platino + Anual = 204.00 (240.00 menos 36.00, como en el mockup M-03)', () => {
    const d = calcularMonto(2000, 12, 1500);
    expect(d.brutoCentavos).toBe(24000);
    expect(d.descuentoCentavos).toBe(3600);
    expect(d.totalCentavos).toBe(20400);
  });

  it('sin descuento no cambia el bruto', () => {
    expect(calcularMonto(500, 1, 0)).toEqual({
      brutoCentavos: 500,
      descuentoCentavos: 0,
      totalCentavos: 500,
    });
  });

  it('redondea a 2 decimales con ROUND_HALF_UP', () => {
    // 0.05 × 1 × 0.90 = 0.045 → 0.05
    expect(calcularMonto(5, 1, 1000).totalCentavos).toBe(5);
    // 3.35 × 3 × 0.95 = 9.5475 → 9.55
    expect(calcularMonto(335, 3, 500).totalCentavos).toBe(955);
    // 0.01 × 1 × 0.95 = 0.0095 → 0.01
    expect(calcularMonto(1, 1, 500).totalCentavos).toBe(1);
  });

  it('arma la vista previa desde el catálogo del contrato', () => {
    const paquete = aPaquete({ id: 3, titulo: 'Chibcha-Platino', subtitulo: '20.00', estado: '' });
    const plan = aPlan({ id: 4, titulo: 'Anual', subtitulo: '12|0.15', estado: '' });
    expect(aMontoTexto(paquete, plan)).toEqual({
      paquete: 'Chibcha-Platino',
      plan: 'anual',
      meses: 12,
      descuentoPct: '15',
      bruto: '240.00',
      descuento: '36.00',
      total: '204.00',
    });
  });

  it('el pipe `monto` agrega la moneda', () => {
    const pipe = new MontoPipe();
    expect(pipe.transform('54.00')).toBe('US$ 54.00');
    expect(pipe.transform(null)).toBe('');
  });
});
