// Interfaces DTO copiadas de docs/api.md (iguales a DC-SRV-01). No agregar campos que no estén en el contrato.

export interface ResultadoAccesoDTO {
  registrado: boolean;
  idUsuario?: number;
  nombre: string;
  correo: string;
  tipoUsuario: 'CLIENTE' | 'EMPLEADO' | '';
  rol?: 'Gestión' | 'Soporte' | 'Administrador';
  operaciones: string[];
}

export interface DatosClienteDTO {
  telefono: string;
  lineaResidencia: string;
  ciudadResidencia: string;
  codigoPostalResidencia: string;
  sitio: string;
  plataforma: 'WINDOWS' | 'UNIX';
  idPaquete: number;
  idPlan: number;
  lineaFacturacion: string;
  ciudadFacturacion: string;
  codigoPostalFacturacion: string;
  numeroTarjeta: string;
  /** AAAA-MM-01 */
  vencimiento: string;
  codigoSeguridad: string;
  franquicia: 'VISA' | 'MASTERCARD' | 'DINERS';
  codigoDistribuidor?: string;
  idSuscripcion?: number;
  /** Solo PATCH PERSONAL y registro */
  nombre?: string;
}

export interface EmpleadoDTO {
  nombre: string;
  documento: string;
  correo: string;
  telefono: string;
  idRol: number;
}

export interface DistribuidorDTO {
  nombre: string;
  documento: string;
  correo: string;
  telefono: string;
}

export interface ResumenDTO {
  id: number;
  titulo: string;
  subtitulo: string;
  estado: string;
}

/** Cada campo: "clave: valor". */
export interface DetalleDTO {
  id: number;
  titulo: string;
  campos: string[];
}

/** entradas: "NIVEL|tipo|idLegado|mensaje" */
export interface ResultadoMigracionDTO {
  idProceso: number;
  validos: number;
  invalidos: number;
  entradas: string[];
}
