import { PATRONES } from '../../../shared/formularios/pago';
import { DatosClienteDTO, DetalleDTO } from '../dto';
import { PAQUETES_SIM, PLANES_SIM } from './catalogo.simulado';
import {
  ClienteSim,
  clienteActual,
  clientes,
  DOMINIO_BASE,
  fallaForzada,
  guardarCliente,
} from './estado';
import { distribuidorActivoPorCodigo } from './gestion.estado';
import { ErrorSim, ManejadorSim, validacion } from './tipos';
import { fijarUsuarioSimulado } from './sesiones';
import {
  calcularMonto,
  centavosADecimal,
  decimalACentavos,
  descuentoAPuntosBasicos,
} from '../../../shared/monto';

type Datos = Partial<DatosClienteDTO>;

const vacio = (v: unknown): boolean => typeof v !== 'string' || v.trim() === '';

function exigir(
  d: Datos,
  campos: (keyof DatosClienteDTO)[],
  nombres: Record<string, string>,
): void {
  for (const c of campos) {
    if (vacio(d[c])) throw validacion(c, `${nombres[c] ?? c} es obligatorio.`);
  }
}

/** Como el backend, cualquier falla de la dirección se informa en el campo de la línea. */
function validarDireccion(linea: string, ciudad: string, cp: string, d: Datos): void {
  const val = (c: string) => String(d[c as keyof DatosClienteDTO] ?? '').trim();
  const tipo = linea === 'lineaResidencia' ? 'residencia' : 'facturación';
  if (!val(linea) || !val(ciudad) || !/^[A-Za-z0-9]{4,10}$/.test(val(cp))) {
    throw validacion(linea, `La dirección de ${tipo} no es válida`);
  }
}

/** RN-16 aplicado al sitio + RN-14 (subdominio único). */
function validarSitio(sitio: string | undefined, propio?: string): void {
  const s = (sitio ?? '').trim().toLowerCase();
  if (!s) throw validacion('sitio', 'El sitio es obligatorio.');
  if (s.length > 63 || !/^[a-z0-9]([a-z0-9-]*[a-z0-9])?$/.test(s)) {
    throw validacion('sitio', 'El nombre del sitio no es válido.');
  }
  if (fallaForzada() === 'contingencia' || s === 'contingencia') {
    throw new ErrorSim(503, {
      codigo: 'CONTINGENCIA',
      mensaje: 'El sistema está en modo contingencia; tu operación quedó respaldada.',
    });
  }
  const ocupado =
    ['www', 'admin', 'correo', 'ocupado'].includes(s) ||
    Object.values(clientes()).some((c) => c.activo && c.sitio === s && c.sitio !== propio);
  if (ocupado) {
    throw new ErrorSim(409, {
      codigo: 'SUBDOMINIO_EN_USO',
      campo: 'sitio',
      mensaje: `El subdominio ${s}.${DOMINIO_BASE} ya está en uso.`,
    });
  }
}

export function validarPersonal(d: Datos, propio?: string): void {
  exigir(d, ['nombre', 'telefono'], { nombre: 'El nombre', telefono: 'El teléfono' });
  const digitos = String(d.telefono).replace(/\D/g, '').length;
  if (digitos < 7 || digitos > 15) throw validacion('telefono', 'El teléfono no es válido.');
  validarDireccion('lineaResidencia', 'ciudadResidencia', 'codigoPostalResidencia', d);
  if (d.plataforma !== 'WINDOWS' && d.plataforma !== 'UNIX') {
    throw validacion('plataforma', 'La plataforma debe ser Windows o Unix.');
  }
  validarSitio(d.sitio, propio);
}

export function validarPlan(d: Datos): void {
  if (!PAQUETES_SIM.some((p) => p.id === d.idPaquete)) {
    throw validacion('idPaquete', 'El paquete no existe.');
  }
  if (!PLANES_SIM.some((p) => p.id === d.idPlan)) throw validacion('idPlan', 'El plan no existe.');
}

/** RN-10 y RN-11, con el validador simulado (D-06: rechaza tarjetas que terminan en 0002). */
export function validarPago(d: Datos, hoy = new Date()): void {
  validarDireccion('lineaFacturacion', 'ciudadFacturacion', 'codigoPostalFacturacion', d);
  const f = d.franquicia;
  if (!f || !(f in PATRONES)) throw validacion('franquicia', 'La franquicia no es válida.');
  exigir(d, ['numeroTarjeta', 'vencimiento', 'codigoSeguridad'], {
    numeroTarjeta: 'El número de tarjeta',
    vencimiento: 'El vencimiento',
    codigoSeguridad: 'El código de seguridad',
  });
  const numero = String(d.numeroTarjeta);
  if (!PATRONES[f].test(numero)) {
    throw validacion('numeroTarjeta', `El número no corresponde a una tarjeta ${f} válida.`);
  }
  const m = /^(\d{4})-(\d{2})-01$/.exec(String(d.vencimiento));
  if (!m) throw validacion('vencimiento', 'El vencimiento debe tener la forma AAAA-MM-01.');
  const anio = Number(m[1]);
  const mes = Number(m[2]);
  if (anio < hoy.getFullYear() || (anio === hoy.getFullYear() && mes < hoy.getMonth() + 1)) {
    throw validacion('vencimiento', 'La tarjeta está vencida.');
  }
  if (!/^\d{3,4}$/.test(String(d.codigoSeguridad))) {
    throw validacion('codigoSeguridad', 'El código de seguridad debe tener 3 o 4 dígitos.');
  }
  if (numero.endsWith('0002')) {
    throw validacion(
      'numeroTarjeta',
      'La tarjeta fue rechazada por el verificador. Revisa el número y la fecha de vencimiento.',
    );
  }
}

function hoyIso(): string {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, '0')}-${String(h.getDate()).padStart(2, '0')}`;
}

/** `registrarse(datos)`: valida como el servicio y crea el cliente (RN-04: corte = hoy). */
export function registrarSim(d: DatosClienteDTO, nombre: string, correo: string): ClienteSim {
  if (fallaForzada() === 'contingencia') {
    throw new ErrorSim(503, { codigo: 'CONTINGENCIA', mensaje: 'Contingencia activa.' });
  }
  validarPersonal({ ...d, nombre: d.nombre ?? nombre });
  validarPlan(d);
  validarPago(d);
  let distribuidor = '';
  if (d.codigoDistribuidor) {
    const dist = distribuidorActivoPorCodigo(d.codigoDistribuidor);
    if (!dist) {
      throw validacion(
        'codigoDistribuidor',
        'El código de distribuidor no existe o no está activo.',
      );
    }
    distribuidor = `${dist.nombre} (${dist.codigo})`;
  }
  const cliente: ClienteSim = {
    idUsuario: 100 + Object.keys(clientes()).length,
    nombre: (d.nombre ?? nombre).trim(),
    correo,
    activo: true,
    telefono: d.telefono.trim(),
    lineaResidencia: d.lineaResidencia.trim(),
    ciudadResidencia: d.ciudadResidencia.trim(),
    codigoPostalResidencia: d.codigoPostalResidencia.trim(),
    lineaFacturacion: d.lineaFacturacion.trim(),
    ciudadFacturacion: d.ciudadFacturacion.trim(),
    codigoPostalFacturacion: d.codigoPostalFacturacion.trim(),
    ultimos4: d.numeroTarjeta.slice(-4),
    franquicia: d.franquicia,
    vencimiento: d.vencimiento,
    idSuscripcion: 100 + Object.keys(clientes()).length,
    sitio: d.sitio.trim().toLowerCase(),
    plataforma: d.plataforma,
    idPaquete: d.idPaquete,
    idPlan: d.idPlan,
    fechaCorte: hoyIso(),
    distribuidor,
  };
  guardarCliente(cliente);
  return cliente;
}

function montoPeriodo(c: ClienteSim): string {
  const paquete = PAQUETES_SIM.find((p) => p.id === c.idPaquete);
  const plan = PLANES_SIM.find((p) => p.id === c.idPlan);
  if (!paquete || !plan) return '0.00';
  const [meses, descuento] = plan.subtitulo.split('|');
  return centavosADecimal(
    calcularMonto(
      decimalACentavos(paquete.subtitulo),
      Number(meses),
      descuentoAPuntosBasicos(descuento),
    ).totalCentavos,
  );
}

/** `DetalleDTO` de CLIENTE con las claves fijas de api.md. */
export function detalleDe(c: ClienteSim): DetalleDTO {
  const paquete = PAQUETES_SIM.find((p) => p.id === c.idPaquete);
  const plan = PLANES_SIM.find((p) => p.id === c.idPlan);
  const campos: [string, string | number | boolean][] = [
    ['nombre', c.nombre],
    ['correo', c.correo],
    ['telefono', c.telefono],
    ['lineaResidencia', c.lineaResidencia],
    ['ciudadResidencia', c.ciudadResidencia],
    ['codigoPostalResidencia', c.codigoPostalResidencia],
    ['lineaFacturacion', c.lineaFacturacion],
    ['ciudadFacturacion', c.ciudadFacturacion],
    ['codigoPostalFacturacion', c.codigoPostalFacturacion],
    ['tarjeta', `${c.franquicia} •••• ${c.ultimos4}`],
    ['franquicia', c.franquicia],
    ['vencimiento', c.vencimiento],
    ['idSuscripcion', c.idSuscripcion],
    ['sitio', `${c.sitio}.${DOMINIO_BASE}`],
    ['plataforma', c.plataforma],
    ['idPaquete', c.idPaquete],
    ['paquete', paquete?.titulo ?? ''],
    ['idPlan', c.idPlan],
    ['plan', plan?.titulo ?? ''],
    ['montoPeriodo', montoPeriodo(c)],
    ['fechaCorte', c.fechaCorte],
    ['distribuidor', c.distribuidor],
    ['activo', c.activo],
  ];
  return { id: c.idUsuario, titulo: c.nombre, campos: campos.map(([k, v]) => `${k}: ${v}`) };
}

function exigirCliente(): ClienteSim {
  const c = clienteActual();
  if (!c) throw new ErrorSim(401, { codigo: 'NO_AUTENTICADO', mensaje: 'No hay sesión' });
  return c;
}

export const clientesSimulado: ManejadorSim = (p) => {
  if (p.ruta !== '/clientes/me') return undefined;
  const c = exigirCliente();

  if (p.metodo === 'GET') return { estado: 200, cuerpo: detalleDe(c) };

  if (p.metodo === 'PATCH') {
    const d = (p.cuerpo ?? {}) as Datos;
    const categoria = p.query.get('categoria');
    const nuevo = { ...c };
    if (categoria === 'PERSONAL') {
      validarPersonal(d, c.sitio);
      Object.assign(nuevo, {
        nombre: d.nombre!.trim(),
        telefono: d.telefono!.trim(),
        lineaResidencia: d.lineaResidencia!.trim(),
        ciudadResidencia: d.ciudadResidencia!.trim(),
        codigoPostalResidencia: d.codigoPostalResidencia!.trim(),
        sitio: d.sitio!.trim().toLowerCase(),
        plataforma: d.plataforma,
      });
    } else if (categoria === 'PAQUETE_PLAN') {
      if (d.idSuscripcion !== c.idSuscripcion) {
        throw new ErrorSim(404, { codigo: 'NO_ENCONTRADO', mensaje: 'La suscripción no existe.' });
      }
      validarPlan(d);
      Object.assign(nuevo, { idPaquete: d.idPaquete, idPlan: d.idPlan });
    } else if (categoria === 'PAGO') {
      if (fallaForzada() === 'contingencia') {
        throw new ErrorSim(503, { codigo: 'CONTINGENCIA', mensaje: 'Contingencia activa.' });
      }
      validarPago(d);
      Object.assign(nuevo, {
        lineaFacturacion: d.lineaFacturacion!.trim(),
        ciudadFacturacion: d.ciudadFacturacion!.trim(),
        codigoPostalFacturacion: d.codigoPostalFacturacion!.trim(),
        ultimos4: d.numeroTarjeta!.slice(-4),
        franquicia: d.franquicia,
        vencimiento: d.vencimiento,
      });
    } else {
      throw new ErrorSim(400, { codigo: 'SOLICITUD_INVALIDA', mensaje: 'Categoría desconocida.' });
    }
    guardarCliente(nuevo);
    return { estado: 204 };
  }

  if (p.metodo === 'DELETE') {
    if (fallaForzada() === 'contingencia') {
      throw new ErrorSim(503, { codigo: 'CONTINGENCIA', mensaje: 'Contingencia activa.' });
    }
    guardarCliente({ ...c, activo: false });
    fijarUsuarioSimulado('anonimo');
    return { estado: 204 };
  }
  return undefined;
};
