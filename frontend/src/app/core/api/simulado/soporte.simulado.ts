import { DetalleDTO, ResumenDTO } from '../dto';
import { guardar, leer } from './almacen';
import {
  dosDigitos,
  estadoInvalido,
  exigirAutenticado,
  exigirOperacion,
  exigirSesionCliente,
  fechaHoraLocal,
  fechaLocalDe,
  noEncontrado,
} from './comun';
import { clienteActual, DOMINIO_BASE } from './estado';
import { ErrorSim, ManejadorSim, PeticionSim, validacion } from './tipos';

/** Niveles de servicio: Soporte (1) → Gestión (2) → Desarrollo (3, último). */
export const NIVELES_SIM = ['Soporte', 'Gestión', 'Desarrollo'];

interface TicketSim {
  id: number;
  categoria: string;
  estado: 'ABIERTO' | 'ESCALADO' | 'RESUELTO';
  nivel: 1 | 2 | 3;
  reportante: string;
  correo: string;
  sitio: string;
  /** ISO 8601 con zona. */
  fechaCreacion: string;
  descripcion: string;
  movimientos: string[];
}

function hace(dias: number, hora: number, minuto: number): string {
  const d = new Date();
  d.setDate(d.getDate() - dias);
  d.setHours(hora, minuto, 0, 0);
  return d.toISOString();
}

const SITIO_STEVEN = `cafedeboyaca.${DOMINIO_BASE}`;

/** Tickets sembrados (relativos a hoy) con los datos de los mockups M-10 y M-17. */
function semilla(): TicketSim[] {
  const base = {
    movimientos: [] as string[],
    nivel: 1 as const,
    estado: 'ABIERTO' as const,
  };
  const steven = { reportante: 'Steven Navarro (cliente)', correo: 'steven@correo.co' };
  return [
    {
      ...base,
      ...steven,
      id: 1042,
      categoria: 'RENDIMIENTO',
      sitio: SITIO_STEVEN,
      fechaCreacion: hace(0, 9, 14),
      descripcion: 'El sitio tarda más de 10 segundos en cargar desde esta mañana.',
    },
    {
      ...base,
      id: 1041,
      categoria: 'CORREO',
      reportante: 'Paula Ríos (cliente)',
      correo: 'paula.rios@correo.com',
      sitio: `artesaniasraquira.${DOMINIO_BASE}`,
      fechaCreacion: hace(0, 8, 40),
      descripcion: 'No puedo enviar correos desde mi cuenta del dominio.',
    },
    {
      ...base,
      ...steven,
      id: 1038,
      categoria: 'CORREO',
      estado: 'ESCALADO',
      nivel: 2,
      sitio: SITIO_STEVEN,
      fechaCreacion: hace(1, 16, 5),
      descripcion: 'Los correos del dominio llegan a spam.',
      movimientos: [
        `${fechaHoraLocal(new Date(hace(1, 16, 50)))}|Sergio Soporte|ESCALADO|Gestión|Requiere revisión de la configuración del dominio.`,
      ],
    },
    {
      ...base,
      id: 1035,
      categoria: 'DOMINIO',
      reportante: 'Hostal Iza (cliente)',
      correo: 'reservas@hostaliza.co',
      sitio: `hostaliza.${DOMINIO_BASE}`,
      fechaCreacion: hace(2, 11, 20),
      descripcion: 'Pedí un dominio hace días y no veo respuesta.',
    },
    {
      ...base,
      id: 1029,
      categoria: 'OTRA',
      estado: 'ESCALADO',
      nivel: 3,
      reportante: 'Gabriela Gestión (empleado)',
      correo: 'gestion@chibchaweb.co',
      sitio: '',
      fechaCreacion: hace(4, 14, 0),
      descripcion: 'El reporte mensual de comisiones tarda demasiado en abrir.',
      movimientos: [
        `${fechaHoraLocal(new Date(hace(4, 14, 30)))}|Sergio Soporte|ESCALADO|Gestión|Se revisó el reporte sin hallazgos.`,
        `${fechaHoraLocal(new Date(hace(3, 9, 10)))}|Gabriela Gestión|ESCALADO|Desarrollo|Caché saturada; se requiere revisión de desarrollo.`,
      ],
    },
    {
      ...base,
      id: 1020,
      categoria: 'BASE_DATOS',
      estado: 'RESUELTO',
      reportante: 'Diego Camargo (cliente)',
      correo: 'dcamargo@correo.com',
      sitio: `dcfotografia.${DOMINIO_BASE}`,
      fechaCreacion: hace(6, 10, 0),
      descripcion: 'No puedo conectarme a la base de datos del sitio.',
      movimientos: [
        `${fechaHoraLocal(new Date(hace(6, 12, 0)))}|Sergio Soporte|RESUELTO|Soporte|Se restableció la conexión.`,
      ],
    },
    {
      ...base,
      ...steven,
      id: 991,
      categoria: 'DOMINIO',
      estado: 'RESUELTO',
      sitio: SITIO_STEVEN,
      fechaCreacion: hace(9, 15, 0),
      descripcion: 'El dominio no resuelve.',
      movimientos: [
        `${fechaHoraLocal(new Date(hace(9, 16, 0)))}|Sergio Soporte|RESUELTO|Soporte|Se corrigió el registro DNS.`,
      ],
    },
  ];
}

const tickets = (): TicketSim[] => {
  const guardados = leer<TicketSim[] | null>('tickets', null);
  if (guardados) return guardados;
  const inicial = semilla();
  guardar('tickets', inicial);
  return inicial;
};

const nombreNivel = (n: number): string => NIVELES_SIM[n - 1] ?? '';

const resumen = (t: TicketSim): ResumenDTO => ({
  id: t.id,
  titulo: t.categoria,
  subtitulo: nombreNivel(t.nivel),
  estado: t.estado,
});

const detalle = (t: TicketSim): DetalleDTO => ({
  id: t.id,
  titulo: `Ticket #${t.id}`,
  campos: [
    `categoria: ${t.categoria}`,
    `estado: ${t.estado}`,
    `nivel: ${nombreNivel(t.nivel)}`,
    `reportante: ${t.reportante}`,
    `sitio: ${t.sitio}`,
    `fechaCreacion: ${t.fechaCreacion}`,
    `descripcion: ${t.descripcion}`,
    ...t.movimientos.map((m) => `movimiento: ${m}`),
  ],
});

const porId = (id: number): TicketSim => {
  const t = tickets().find((x) => x.id === id);
  if (!t) throw noEncontrado('El ticket');
  return t;
};

const masReciente = (a: TicketSim, b: TicketSim): number =>
  b.fechaCreacion.localeCompare(a.fechaCreacion) || b.id - a.id;

/** RN-24: creados ese día más todos los que siguen abiertos, sin repetir, del más reciente al más antiguo. */
function diarios(fecha: string): TicketSim[] {
  return tickets()
    .filter((t) => fechaLocalDe(t.fechaCreacion) === fecha || t.estado !== 'RESUELTO')
    .sort(masReciente);
}

function guardarTicket(t: TicketSim): void {
  guardar(
    'tickets',
    tickets().map((x) => (x.id === t.id ? t : x)),
  );
}

function crear(cuerpo: unknown): TicketSim {
  const s = exigirAutenticado();
  const d = (cuerpo ?? {}) as { categoria?: unknown; descripcion?: unknown; idSitio?: unknown };
  // El contrato usa el literal del enum (RENDIMIENTO, BASE_DATOS, …).
  const categoria = typeof d.categoria === 'string' ? d.categoria.trim().toUpperCase() : '';
  const descripcion = typeof d.descripcion === 'string' ? d.descripcion.trim() : '';
  if (!categoria) throw validacion('categoria', 'El tipo de novedad es obligatorio.');
  if (!descripcion) throw validacion('descripcion', 'La descripción es obligatoria.');
  let sitio = '';
  if (d.idSitio !== undefined && d.idSitio !== null) {
    // RN-22: el sitio, si viene, tiene que ser de un sitio del cliente.
    const c = clienteActual();
    if (!c || c.idSuscripcion !== d.idSitio) {
      throw new ErrorSim(422, {
        codigo: 'REGLA_NEGOCIO',
        mensaje: 'El sitio indicado no pertenece al cliente.',
        campo: 'idSitio',
      });
    }
    sitio = `${c.sitio}.${DOMINIO_BASE}`;
  }
  const lista = tickets();
  const nuevo: TicketSim = {
    id: Math.max(0, ...lista.map((x) => x.id)) + 1,
    categoria,
    estado: 'ABIERTO',
    nivel: 1,
    reportante: `${s.nombre} (${s.tipoUsuario === 'CLIENTE' ? 'cliente' : 'empleado'})`,
    correo: s.correo,
    sitio,
    fechaCreacion: new Date().toISOString(),
    descripcion,
    movimientos: [],
  };
  guardar('tickets', [...lista, nuevo]);
  return nuevo;
}

/** RN-23: escalar o resolver con observación obligatoria; cada cambio deja un movimiento. */
function enrutar(id: number, cuerpo: unknown): void {
  const s = exigirOperacion('ATENDER_TICKETS');
  const t = porId(id);
  const d = (cuerpo ?? {}) as { escalar?: unknown; observacion?: unknown };
  const observacion = typeof d.observacion === 'string' ? d.observacion.trim() : '';
  if (!observacion) throw validacion('observacion', 'La observación es obligatoria.');
  if (typeof d.escalar !== 'boolean') {
    throw new ErrorSim(400, { codigo: 'SOLICITUD_INVALIDA', mensaje: 'Falta `escalar`.' });
  }
  let nuevo: TicketSim;
  if (d.escalar) {
    if (t.estado === 'RESUELTO') throw estadoInvalido('El ticket ya está resuelto.');
    if (t.nivel === NIVELES_SIM.length) {
      throw estadoInvalido('El ticket ya está en el último nivel de servicio.');
    }
    nuevo = { ...t, nivel: (t.nivel + 1) as 2 | 3, estado: 'ESCALADO' };
  } else {
    nuevo = { ...t, estado: 'RESUELTO' };
  }
  nuevo.movimientos = [
    ...t.movimientos,
    `${fechaHoraLocal()}|${s.nombre}|${nuevo.estado}|${nombreNivel(nuevo.nivel)}|${observacion}`,
  ];
  guardarTicket(nuevo);
}

const FECHA = /^\d{4}-\d{2}-\d{2}$/;
const hoy = (): string => {
  const h = new Date();
  return `${h.getFullYear()}-${dosDigitos(h.getMonth() + 1)}-${dosDigitos(h.getDate())}`;
};

const coincide = (filtro: string, t: TicketSim): boolean => {
  const f = filtro.trim().toLowerCase();
  return !f || t.descripcion.toLowerCase().includes(f) || String(t.id).includes(f);
};

export const soporteSimulado: ManejadorSim = (p: PeticionSim) => {
  const clave = `${p.metodo} ${p.ruta}`;

  if (clave === 'GET /clientes/me/sitios') {
    exigirSesionCliente();
    const c = clienteActual();
    return {
      estado: 200,
      cuerpo: c
        ? [
            {
              id: c.idSuscripcion,
              titulo: `${c.sitio}.${DOMINIO_BASE}`,
              subtitulo: c.plataforma,
              estado: 'ACTIVO',
            },
          ]
        : [],
    };
  }

  if (clave === 'POST /tickets') {
    return { estado: 201, cuerpo: { id: crear(p.cuerpo).id } };
  }
  if (clave === 'GET /tickets/mios') {
    const s = exigirAutenticado();
    return {
      estado: 200,
      cuerpo: tickets()
        .filter((t) => t.correo === s.correo)
        .sort(masReciente)
        .map(resumen),
    };
  }
  if (clave === 'GET /tickets/diarios') {
    exigirOperacion('ATENDER_TICKETS');
    const fecha = p.query.get('fecha') || hoy();
    if (!FECHA.test(fecha) || Number.isNaN(Date.parse(fecha))) {
      throw validacion('fecha', 'La fecha debe tener el formato AAAA-MM-DD.');
    }
    return { estado: 200, cuerpo: diarios(fecha).map(resumen) };
  }

  const t = /^\/tickets\/(\d+)(\/enrutamiento)?$/.exec(p.ruta);
  if (t) {
    if (p.metodo === 'GET' && !t[2]) {
      exigirOperacion('ATENDER_TICKETS');
      return { estado: 200, cuerpo: detalle(porId(Number(t[1]))) };
    }
    if (p.metodo === 'POST' && t[2]) {
      enrutar(Number(t[1]), p.cuerpo);
      return { estado: 204 };
    }
  }

  // GET /consultas/TICKET[/id]: el mismo detalle con el permiso ATENDER_TICKETS (CU-CON-01/02).
  const c = /^\/consultas\/TICKET(?:\/(\d+))?$/.exec(p.ruta);
  if (c && p.metodo === 'GET') {
    exigirOperacion('ATENDER_TICKETS');
    return {
      estado: 200,
      cuerpo: c[1]
        ? detalle(porId(Number(c[1])))
        : tickets()
            .filter((x) => coincide(p.query.get('filtro') ?? '', x))
            .sort(masReciente)
            .map(resumen),
    };
  }
  return undefined;
};
