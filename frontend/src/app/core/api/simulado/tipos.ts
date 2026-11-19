export interface PeticionSim {
  metodo: string;
  ruta: string;
  query: URLSearchParams;
  cuerpo: unknown;
}

export interface RespuestaSim {
  estado: number;
  cuerpo?: unknown;
}

/** Error con el cuerpo único de docs/api.md. */
export class ErrorSim extends Error {
  constructor(
    readonly estado: number,
    readonly cuerpo: { codigo: string; mensaje: string; campo?: string },
  ) {
    super(cuerpo.mensaje);
  }
}

export const validacion = (campo: string, mensaje: string): ErrorSim =>
  new ErrorSim(422, { codigo: 'VALIDACION', mensaje, campo });

export type ManejadorSim = (p: PeticionSim) => RespuestaSim | undefined;
