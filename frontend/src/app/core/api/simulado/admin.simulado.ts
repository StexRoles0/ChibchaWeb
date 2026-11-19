import { ResultadoMigracionDTO } from '../dto';
import { ALGORITMOS } from '../contingencia.api';
import { guardar, leer } from './almacen';
import { contingenciaActiva, estadoInvalido, exigirOperacion, noEncontrado } from './comun';
import { fallaForzada } from './estado';
import { ManejadorSim, validacion } from './tipos';

// ---- Contingencia (RT04) ----

interface EventoRespaldo {
  id: number;
  tipoEvento: string;
  algoritmo: string;
}

/** Los tres eventos del mockup M-20, con el tipo técnico (`Agregado.operacion`) del backend. */
const EVENTOS_INICIALES: EventoRespaldo[] = [
  { id: 1, tipoEvento: 'Suscripcion.registrar_pago', algoritmo: 'AES' },
  { id: 2, tipoEvento: 'SolicitudDominio.insertar', algoritmo: 'AES' },
  { id: 3, tipoEvento: 'Comision.registrar_cheque', algoritmo: 'ChaCha20' },
];

const respaldo = (): EventoRespaldo[] => leer('respaldo', EVENTOS_INICIALES);
const algoritmoActivo = (): string => leer('algoritmo', 'AES');

/** Una escritura que devolvió 503 deja su evento en el respaldo, cifrado con el algoritmo activo. */
export function agregarRespaldo(tipoEvento: string): void {
  const lista = respaldo();
  guardar('respaldo', [
    ...lista,
    { id: Math.max(0, ...lista.map((e) => e.id)) + 1, tipoEvento, algoritmo: algoritmoActivo() },
  ]);
}

// ---- Migración (CU-MIG-01) ----

type EstadoProceso = 'CREADA' | 'SIMULADA' | 'APROBADA' | 'EJECUTADA' | 'REVERTIDA' | 'CANCELADA';

interface ProcesoSim {
  id: number;
  estado: EstadoProceso;
  validos: number;
  invalidos: number;
  entradas: string[];
}

/** Log de la simulación sobre los registros legados de ejemplo (clientes, hosting y pagos). */
function entradasSimuladas(): string[] {
  const e: string[] = [];
  for (let i = 1; i <= 8; i++) {
    const id = `CL-${String(i).padStart(4, '0')}`;
    if (i === 4) e.push(`ERROR|CLIENTE|${id}|Dirección: la línea es obligatoria`);
    else if (i === 7) e.push(`ERROR|CLIENTE|${id}|Tarjeta: la tarjeta está vencida`);
    else e.push(`INFO|CLIENTE|${id}|Registro válido`);
  }
  for (let i = 1; i <= 6; i++) {
    const id = `HO-${String(i).padStart(4, '0')}`;
    if (i === 5) e.push(`ERROR|HOSTING|${id}|El plan indicado no existe en el catálogo`);
    else e.push(`INFO|HOSTING|${id}|Paquete, plan y plataforma existen en el catálogo`);
  }
  for (let i = 1; i <= 10; i++) {
    const id = `PG-${String(i).padStart(4, '0')}`;
    if (i === 9) e.push(`ERROR|PAGO|${id}|El monto no es válido`);
    else e.push(`INFO|PAGO|${id}|Pago válido`);
  }
  return e;
}

const procesos = (): ProcesoSim[] => leer('migraciones', []);

function proceso(id: number): ProcesoSim {
  const p = procesos().find((x) => x.id === id);
  if (!p) throw noEncontrado('El proceso de migración');
  return p;
}

function guardarProceso(p: ProcesoSim): void {
  guardar(
    'migraciones',
    procesos().map((x) => (x.id === p.id ? p : x)),
  );
}

export const adminSimulado: ManejadorSim = (p) => {
  const clave = `${p.metodo} ${p.ruta}`;

  if (clave === 'GET /contingencia/pendientes') {
    exigirOperacion('GESTIONAR_CONTINGENCIA');
    return {
      estado: 200,
      cuerpo: respaldo().map((e) => ({
        id: e.id,
        titulo: e.tipoEvento,
        subtitulo: e.algoritmo,
        estado: 'PENDIENTE',
      })),
    };
  }
  if (clave === 'PUT /contingencia/algoritmo') {
    exigirOperacion('GESTIONAR_CONTINGENCIA');
    const nombre = (p.cuerpo as { nombre?: unknown } | null)?.nombre;
    if (!(ALGORITMOS as readonly unknown[]).includes(nombre)) {
      throw validacion('nombre', 'El algoritmo no está admitido.');
    }
    guardar('algoritmo', nombre);
    return { estado: 204 };
  }
  if (clave === 'POST /contingencia/sincronizacion') {
    exigirOperacion('GESTIONAR_CONTINGENCIA');
    // RN-30: si la base sigue caída no se sincroniza nada y el respaldo no se vacía.
    if (fallaForzada() === 'contingencia') throw contingenciaActiva();
    const n = respaldo().length;
    guardar('respaldo', []);
    return { estado: 200, cuerpo: { sincronizados: n } };
  }

  if (clave === 'POST /migraciones') {
    exigirOperacion('MIGRAR_DATOS');
    const lista = procesos();
    const entradas = entradasSimuladas();
    const nuevo: ProcesoSim = {
      id: Math.max(0, ...lista.map((x) => x.id)) + 1,
      estado: 'SIMULADA',
      invalidos: entradas.filter((x) => x.startsWith('ERROR|')).length,
      validos: entradas.filter((x) => !x.startsWith('ERROR|')).length,
      entradas,
    };
    guardar('migraciones', [...lista, nuevo]);
    const cuerpo: ResultadoMigracionDTO = {
      idProceso: nuevo.id,
      validos: nuevo.validos,
      invalidos: nuevo.invalidos,
      entradas,
    };
    return { estado: 201, cuerpo };
  }

  const m = /^\/migraciones\/(\d+)\/(confirmacion|cancelacion)$/.exec(p.ruta);
  if (m && p.metodo === 'POST') {
    exigirOperacion('MIGRAR_DATOS');
    const proc = proceso(Number(m[1]));
    if (m[2] === 'confirmacion') {
      // RN-25: solo se confirma una migración simulada; dos veces o sin simular es un 409.
      if (proc.estado !== 'SIMULADA') {
        throw estadoInvalido(
          `La migración está ${proc.estado.toLowerCase()} y no se puede confirmar.`,
        );
      }
      // RN-27: si alguna escritura falla, todo se revierte.
      const estado: EstadoProceso = fallaForzada() === 'migracion' ? 'REVERTIDA' : 'EJECUTADA';
      guardarProceso({ ...proc, estado });
      return { estado: 200, cuerpo: { estado } };
    }
    if (proc.estado !== 'CREADA' && proc.estado !== 'SIMULADA') {
      throw estadoInvalido(
        `La migración está ${proc.estado.toLowerCase()} y no se puede cancelar.`,
      );
    }
    guardarProceso({ ...proc, estado: 'CANCELADA' });
    return { estado: 200, cuerpo: { estado: 'CANCELADA' } };
  }
  return undefined;
};
