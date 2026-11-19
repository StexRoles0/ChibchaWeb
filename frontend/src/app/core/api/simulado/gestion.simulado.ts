import { DetalleDTO, DistribuidorDTO, EmpleadoDTO, ResumenDTO } from '../dto';
import { PAQUETES_SIM } from './catalogo.simulado';
import { ClienteSim, clientes, DOMINIO_BASE, fallaForzada } from './estado';
import { detalleDe } from './clientes.simulado';
import {
  categoriaDe,
  DistribuidorSim,
  distribuidores,
  EmpleadoSim,
  empleados,
  generarCodigoDistribuidor,
  guardarDistribuidores,
  guardarEmpleados,
  hoyIso,
  referidosDe,
  ROLES_SIM,
} from './gestion.estado';
import { sesionActual } from './estado';
import { ErrorSim, ManejadorSim, PeticionSim, validacion } from './tipos';

/** Clientes de demostración (solo lectura) para que el listado de M-16 tenga datos. */
const CLIENTES_DEMO: ClienteSim[] = [
  demo(11, 'Paula Ríos', 'paula.rios@correo.com', 'artesaniasraquira', 2, true),
  demo(12, 'Hostal Iza', 'reservas@hostaliza.co', 'hostaliza', 1, true),
  demo(13, 'Diego Camargo', 'dcamargo@correo.com', 'dcfotografia', 2, false),
];

function demo(
  id: number,
  nombre: string,
  correo: string,
  sitio: string,
  idPaquete: number,
  activo: boolean,
): ClienteSim {
  return {
    idUsuario: id,
    nombre,
    correo,
    activo,
    telefono: '3105550000',
    lineaResidencia: 'Carrera 10 # 5-20',
    ciudadResidencia: 'Tunja',
    codigoPostalResidencia: '150001',
    lineaFacturacion: 'Carrera 10 # 5-20',
    ciudadFacturacion: 'Tunja',
    codigoPostalFacturacion: '150001',
    ultimos4: '4242',
    franquicia: 'VISA',
    vencimiento: '2029-05-01',
    idSuscripcion: id,
    sitio,
    plataforma: 'UNIX',
    idPaquete,
    idPlan: 3,
    fechaCorte: '2027-01-15',
    distribuidor: '',
  };
}

const estadoDe = (activo: boolean): string => (activo ? 'ACTIVO' : 'INACTIVO');
const rolDe = (id: number): string => ROLES_SIM.find((r) => r.id === id)?.titulo ?? '';

const noEncontrado = (que: string): ErrorSim =>
  new ErrorSim(404, { codigo: 'NO_ENCONTRADO', mensaje: `${que} no existe.` });

const contingencia = (): ErrorSim =>
  new ErrorSim(503, {
    codigo: 'CONTINGENCIA',
    mensaje:
      'El sistema está en modo contingencia; tu operación quedó respaldada y se aplicará al restablecerse el servicio.',
  });

function permiso(operacion: string): void {
  const s = sesionActual();
  if (!s) throw new ErrorSim(401, { codigo: 'NO_AUTENTICADO', mensaje: 'No hay sesión.' });
  if (!s.operaciones.includes(operacion)) {
    throw new ErrorSim(403, { codigo: 'SIN_PERMISO', mensaje: 'No tienes permiso.' });
  }
}

const coincide = (filtro: string, ...textos: string[]): boolean => {
  const f = filtro.trim().toLowerCase();
  return !f || textos.some((t) => t.toLowerCase().includes(f));
};

// ---- Validación (mismas reglas que el servicio: campos vacíos, formato, unicidad) ----

const txt = (v: unknown): string => (typeof v === 'string' ? v.trim() : '');

function validarPersona(d: Partial<EmpleadoDTO>): void {
  if (!txt(d.nombre)) throw validacion('nombre', 'El nombre es obligatorio.');
  if (!txt(d.documento)) throw validacion('documento', 'El documento es obligatorio.');
  if (!/^[A-Za-z0-9.\- ]{4,20}$/.test(txt(d.documento))) {
    throw validacion('documento', 'El documento no es válido.');
  }
  if (!txt(d.correo)) throw validacion('correo', 'El correo es obligatorio.');
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(txt(d.correo))) {
    throw validacion('correo', 'El correo no es válido.');
  }
  if (!txt(d.telefono)) throw validacion('telefono', 'El teléfono es obligatorio.');
  const digitos = txt(d.telefono).replace(/\D/g, '').length;
  if (digitos < 7 || digitos > 15) throw validacion('telefono', 'El teléfono no es válido.');
}

/** RN-05 y CU-EMP: correo y documento únicos. El correo se compara entre todos los usuarios. */
function validarUnicos(d: { documento: string; correo: string }, tipo: 'e' | 'd', propio?: number) {
  const correo = txt(d.correo).toLowerCase();
  const documento = txt(d.documento).toLowerCase();
  const mismo = (id: number, tipoFila: 'e' | 'd') => tipoFila === tipo && id === propio;
  const filas: { id: number; tipo: 'e' | 'd'; correo: string; documento: string }[] = [
    ...empleados().map((e) => ({ ...e, tipo: 'e' as const })),
    ...distribuidores().map((x) => ({ ...x, tipo: 'd' as const })),
  ];
  for (const f of filas) {
    if (mismo(f.id, f.tipo)) continue;
    if (f.correo.toLowerCase() === correo) {
      throw new ErrorSim(409, {
        codigo: 'DUPLICADO',
        mensaje: 'Ya existe un usuario con ese correo.',
        campo: 'correo',
      });
    }
    if (f.tipo === tipo && f.documento.toLowerCase() === documento) {
      throw new ErrorSim(409, {
        codigo: 'DUPLICADO',
        mensaje: 'Ya existe un registro con ese documento.',
        campo: 'documento',
      });
    }
  }
  if (
    Object.values(clientes()).some((c) => c.correo.toLowerCase() === correo) ||
    CLIENTES_DEMO.some((c) => c.correo.toLowerCase() === correo)
  ) {
    throw new ErrorSim(409, {
      codigo: 'DUPLICADO',
      mensaje: 'Ya existe un usuario con ese correo.',
      campo: 'correo',
    });
  }
}

function limpiar<T extends Partial<EmpleadoDTO>>(d: T) {
  return {
    nombre: txt(d.nombre),
    documento: txt(d.documento),
    correo: txt(d.correo),
    telefono: txt(d.telefono),
  };
}

// ---- Resúmenes y detalles (claves fijas de api.md) ----

const resumenEmpleado = (e: EmpleadoSim): ResumenDTO => ({
  id: e.id,
  titulo: e.nombre,
  subtitulo: `${e.documento} · ${rolDe(e.idRol)}`,
  estado: estadoDe(e.activo),
});

const resumenDistribuidor = (d: DistribuidorSim): ResumenDTO => ({
  id: d.id,
  titulo: d.nombre,
  subtitulo: `${d.documento} · ${d.codigo} · ${referidosDe(d)} referidos`,
  estado: estadoDe(d.activo),
});

const todosLosClientes = (): ClienteSim[] => [...CLIENTES_DEMO, ...Object.values(clientes())];

const resumenCliente = (c: ClienteSim): ResumenDTO => ({
  id: c.idUsuario,
  titulo: c.nombre,
  subtitulo: `${c.correo} · ${c.sitio}.${DOMINIO_BASE} · ${PAQUETES_SIM.find((p) => p.id === c.idPaquete)?.titulo ?? ''}`,
  estado: estadoDe(c.activo),
});

const armar = (
  id: number,
  titulo: string,
  pares: [string, string | number | boolean][],
): DetalleDTO => ({
  id,
  titulo,
  campos: pares.map(([k, v]) => `${k}: ${v}`),
});

const detalleEmpleado = (e: EmpleadoSim): DetalleDTO =>
  armar(e.id, e.nombre, [
    ['nombre', e.nombre],
    ['documento', e.documento],
    ['correo', e.correo],
    ['telefono', e.telefono],
    ['idRol', e.idRol],
    ['rol', rolDe(e.idRol)],
    ['activo', e.activo],
    ['fechaRegistro', e.fechaRegistro],
  ]);

const detalleDistribuidor = (d: DistribuidorSim): DetalleDTO =>
  armar(d.id, d.nombre, [
    ['nombre', d.nombre],
    ['documento', d.documento],
    ['correo', d.correo],
    ['telefono', d.telefono],
    ['codigo', d.codigo],
    ['categoria', categoriaDe(d)],
    ['referidos', referidosDe(d)],
    ['activo', d.activo],
  ]);

// ---- Operaciones ----

function listarEmpleados(filtro: string): ResumenDTO[] {
  return empleados()
    .filter((e) => coincide(filtro, e.nombre, e.correo, e.documento))
    .map(resumenEmpleado);
}

function listarDistribuidores(filtro: string): ResumenDTO[] {
  return distribuidores()
    .filter((d) => coincide(filtro, d.nombre, d.correo, d.documento))
    .map(resumenDistribuidor);
}

function listarClientes(filtro: string): ResumenDTO[] {
  return todosLosClientes()
    .filter((c) => coincide(filtro, c.nombre, c.correo, c.sitio))
    .map(resumenCliente);
}

function empleadoPorId(id: number): EmpleadoSim {
  const e = empleados().find((x) => x.id === id);
  if (!e) throw noEncontrado('El empleado');
  return e;
}

function distribuidorPorId(id: number): DistribuidorSim {
  const d = distribuidores().find((x) => x.id === id);
  if (!d) throw noEncontrado('El distribuidor');
  return d;
}

function clientePorId(id: number): ClienteSim {
  const c = todosLosClientes().find((x) => x.idUsuario === id);
  if (!c) throw noEncontrado('El cliente');
  return c;
}

function escribirEmpleado(id: number | undefined, d: Partial<EmpleadoDTO>): EmpleadoSim {
  if (fallaForzada() === 'contingencia') throw contingencia();
  validarPersona(d);
  if (!ROLES_SIM.some((r) => r.id === d.idRol)) throw validacion('idRol', 'El cargo no existe.');
  const datos = limpiar(d);
  validarUnicos(datos, 'e', id);
  const lista = empleados();
  if (id === undefined) {
    const nuevo: EmpleadoSim = {
      id: Math.max(0, ...lista.map((e) => e.id)) + 1,
      ...datos,
      idRol: d.idRol!,
      activo: true,
      fechaRegistro: hoyIso(),
    };
    guardarEmpleados([...lista, nuevo]);
    return nuevo;
  }
  const actual = empleadoPorId(id);
  const nuevo = { ...actual, ...datos, idRol: d.idRol! };
  guardarEmpleados(lista.map((e) => (e.id === id ? nuevo : e)));
  return nuevo;
}

function escribirDistribuidor(
  id: number | undefined,
  d: Partial<DistribuidorDTO>,
): DistribuidorSim {
  if (fallaForzada() === 'contingencia') throw contingencia();
  validarPersona(d);
  const datos = limpiar(d);
  validarUnicos(datos, 'd', id);
  const lista = distribuidores();
  if (id === undefined) {
    const nuevo: DistribuidorSim = {
      id: Math.max(0, ...lista.map((x) => x.id)) + 1,
      ...datos,
      codigo: generarCodigoDistribuidor(),
      referidosBase: 0,
      activo: true,
    };
    guardarDistribuidores([...lista, nuevo]);
    return nuevo;
  }
  const actual = distribuidorPorId(id);
  const nuevo = { ...actual, ...datos };
  guardarDistribuidores(lista.map((x) => (x.id === id ? nuevo : x)));
  return nuevo;
}

const filtroDe = (p: PeticionSim): string => p.query.get('filtro') ?? '';

interface Recurso {
  operacion: string;
  listar: (f: string) => ResumenDTO[];
  detalle: (id: number) => DetalleDTO;
}

const RECURSOS: Record<string, Recurso> = {
  EMPLEADO: {
    operacion: 'GESTIONAR_EMPLEADOS',
    listar: listarEmpleados,
    detalle: (id) => detalleEmpleado(empleadoPorId(id)),
  },
  DISTRIBUIDOR: {
    operacion: 'GESTIONAR_DISTRIBUIDORES',
    listar: listarDistribuidores,
    detalle: (id) => detalleDistribuidor(distribuidorPorId(id)),
  },
  CLIENTE: {
    operacion: 'CONSULTAR_REGISTROS',
    listar: listarClientes,
    detalle: (id) => detalleDe(clientePorId(id)),
  },
};

export const gestionSimulado: ManejadorSim = (p) => {
  if (p.metodo === 'GET' && p.ruta === '/catalogo/roles') {
    permiso('GESTIONAR_EMPLEADOS');
    return { estado: 200, cuerpo: ROLES_SIM };
  }

  // GET /consultas/{tipo}[/{id}]: los tres tipos de gestión; TICKET lo atiende otro lote.
  const c = /^\/consultas\/(CLIENTE|EMPLEADO|DISTRIBUIDOR)(?:\/(\d+))?$/.exec(p.ruta);
  if (c && p.metodo === 'GET') {
    permiso('CONSULTAR_REGISTROS');
    const r = RECURSOS[c[1]];
    return {
      estado: 200,
      cuerpo: c[2] ? r.detalle(Number(c[2])) : r.listar(filtroDe(p)),
    };
  }

  const m = /^\/(empleados|distribuidores)(?:\/(\d+))?$/.exec(p.ruta);
  if (!m) return undefined;
  const esEmpleado = m[1] === 'empleados';
  const id = m[2] ? Number(m[2]) : undefined;
  const recurso = RECURSOS[esEmpleado ? 'EMPLEADO' : 'DISTRIBUIDOR'];
  permiso(recurso.operacion);

  if (p.metodo === 'GET') {
    return {
      estado: 200,
      cuerpo: id === undefined ? recurso.listar(filtroDe(p)) : recurso.detalle(id),
    };
  }
  if (p.metodo === 'POST' && id === undefined) {
    if (esEmpleado) {
      const e = escribirEmpleado(undefined, (p.cuerpo ?? {}) as Partial<EmpleadoDTO>);
      return { estado: 201, cuerpo: { id: e.id } };
    }
    const d = escribirDistribuidor(undefined, (p.cuerpo ?? {}) as Partial<DistribuidorDTO>);
    return { estado: 201, cuerpo: { id: d.id, codigo: d.codigo } };
  }
  if (p.metodo === 'PUT' && id !== undefined) {
    if (esEmpleado) escribirEmpleado(id, (p.cuerpo ?? {}) as Partial<EmpleadoDTO>);
    else escribirDistribuidor(id, (p.cuerpo ?? {}) as Partial<DistribuidorDTO>);
    return { estado: 204 };
  }
  if (p.metodo === 'DELETE' && id !== undefined) {
    if (fallaForzada() === 'contingencia') throw contingencia();
    if (esEmpleado) {
      const e = empleadoPorId(id);
      guardarEmpleados(empleados().map((x) => (x.id === e.id ? { ...x, activo: false } : x)));
    } else {
      const d = distribuidorPorId(id);
      guardarDistribuidores(
        distribuidores().map((x) => (x.id === d.id ? { ...x, activo: false } : x)),
      );
    }
    return { estado: 204 };
  }
  return undefined;
};
