import { ResumenDTO } from '../dto';
import { EXTENSIONES_DOMINIO } from '../dominios.api';
import { agregarRespaldo } from './admin.simulado';
import { guardar, leer } from './almacen';
import { contingenciaActiva, exigirSesionCliente, fechaLocalDe } from './comun';
import { fallaForzada } from './estado';
import { ManejadorSim, validacion } from './tipos';

interface SolicitudSim {
  id: number;
  correo: string;
  /** Nombre completo con extensión: `cafedeboyaca.com`. */
  dominio: string;
  estado: 'REGISTRADA' | 'ENVIADA' | 'FALLIDA';
  fecha: string;
}

const iso = (dia: string): string => `${dia}T10:30:00-05:00`;

/** Las tres solicitudes del mockup M-09 para el cliente de demostración. */
const INICIALES: SolicitudSim[] = [
  {
    id: 1,
    correo: 'steven@correo.co',
    dominio: 'cafedeboyaca.com',
    estado: 'ENVIADA',
    fecha: iso('2026-09-14'),
  },
  {
    id: 2,
    correo: 'steven@correo.co',
    dominio: 'tostadoresboyaca.co',
    estado: 'FALLIDA',
    fecha: iso('2026-10-02'),
  },
  {
    id: 3,
    correo: 'steven@correo.co',
    dominio: 'cafedeboyaca.net',
    estado: 'REGISTRADA',
    fecha: iso('2026-10-28'),
  },
];

const solicitudes = (): SolicitudSim[] => leer('dominios', INICIALES);

/** RN-16: 1 a 63 caracteres, letras, dígitos y guiones, sin guion al inicio ni al final. */
export const FORMATO_DOMINIO = /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/;

export const dominiosSimulado: ManejadorSim = (p) => {
  if (p.ruta !== '/dominios/solicitudes') return undefined;
  const sesion = exigirSesionCliente();

  if (p.metodo === 'GET') {
    const lista: ResumenDTO[] = solicitudes()
      .filter((s) => s.correo === sesion.correo)
      .sort((a, b) => b.fecha.localeCompare(a.fecha) || b.id - a.id)
      .map((s) => ({
        id: s.id,
        titulo: s.dominio,
        subtitulo: fechaLocalDe(s.fecha),
        estado: s.estado,
      }));
    return { estado: 200, cuerpo: lista };
  }

  if (p.metodo === 'POST') {
    const d = (p.cuerpo ?? {}) as { nombre?: unknown; extension?: unknown };
    const nombre = typeof d.nombre === 'string' ? d.nombre.trim().toLowerCase() : '';
    if (!nombre) throw validacion('nombre', 'El nombre del dominio es obligatorio.');
    if (!FORMATO_DOMINIO.test(nombre)) {
      throw validacion(
        'nombre',
        'El nombre admite de 1 a 63 letras, números y guiones, sin guion al inicio ni al final.',
      );
    }
    if (!(EXTENSIONES_DOMINIO as readonly unknown[]).includes(d.extension)) {
      throw validacion('extension', 'La extensión no está admitida.');
    }
    if (fallaForzada() === 'contingencia') {
      agregarRespaldo('Solicitud de dominio enviada');
      throw contingenciaActiva();
    }
    const lista = solicitudes();
    // D-06: el registrador simulado rechaza los dominios que contienen "rechazo".
    const estado = nombre.includes('rechazo') ? 'FALLIDA' : 'ENVIADA';
    const nueva: SolicitudSim = {
      id: Math.max(0, ...lista.map((s) => s.id)) + 1,
      correo: sesion.correo,
      dominio: `${nombre}${d.extension as string}`,
      estado,
      fecha: new Date().toISOString(),
    };
    guardar('dominios', [...lista, nueva]);
    return { estado: 201, cuerpo: { id: nueva.id, estado } };
  }
  return undefined;
};
