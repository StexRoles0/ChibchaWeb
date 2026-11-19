import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { DistribuidoresApi } from '../../core/api/distribuidores.api';
import { DistribuidorDTO, EmpleadoDTO } from '../../core/api/dto';
import { EmpleadosApi } from '../../core/api/empleados.api';
import { ErrorApi } from '../../core/errores';
import { Campo, OpcionCampo } from '../../shared/campo';
import { campoDelError, ErroresCampo } from '../../shared/errores-formulario';
import { camposDeDetalle } from '../../shared/formato';
import { noVacio, telefono } from '../../shared/formularios/validadores';
import { apiDeTipo, configDeRuta } from './personal';

const requerido = [Validators.required, noVacio];

/**
 * M-13 · Formulario de empleado / distribuidor, reutilizable (CU-EMP-02/03, CU-DIS-02/03).
 * Sin `:id` crea (`POST`); con `:id` carga el detalle y modifica (`PUT`).
 * Los errores 422 y 409 (`campo`) salen bajo el campo; los demás, en el aviso sobre los botones.
 */
@Component({
  selector: 'app-formulario-personal',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, Campo],
  template: `
    <section class="pagina">
      <div>
        <p class="migas">
          <a routerLink="/gestion">Inicio</a> /
          <a [routerLink]="config.ruta">{{ config.plural }}</a> /
          {{ editando ? 'Editar' : 'Nuevo' }}
        </p>
        <h1>{{ editando ? 'Editar' : 'Crear' }} {{ config.singular }}</h1>
        <p class="subtitulo">
          @if (config.tipo === 'empleado') {
            El empleado ingresará con la cuenta externa asociada a este correo.
          } @else {
            El distribuidor no inicia sesión. Su código se genera al guardar.
          }
        </p>
      </div>

      @if (noEncontrado()) {
        <div class="aviso error" role="alert">
          <p>No encontramos {{ config.articulo }} {{ config.singular }} que buscas.</p>
          <a class="boton secundario volver" [routerLink]="config.ruta">Volver al listado</a>
        </div>
      } @else if (cargando()) {
        <p role="status">Cargando datos…</p>
      } @else {
        <form class="tarjeta formulario" [formGroup]="form" (ngSubmit)="guardar()" novalidate>
          <div class="rejilla">
            <app-campo
              nombre="nombre"
              [etiqueta]="config.tipo === 'empleado' ? 'Nombre completo' : 'Nombre o razón social'"
              [control]="form.controls.nombre"
              autocompletar="off"
              [errorServidor]="errores.de('nombre')"
            />
            <app-campo
              nombre="documento"
              etiqueta="Documento de identidad"
              [control]="form.controls.documento"
              autocompletar="off"
              [errorServidor]="errores.de('documento')"
            />
            <app-campo
              nombre="correo"
              etiqueta="Correo electrónico"
              tipo="email"
              [control]="form.controls.correo"
              autocompletar="off"
              [errorServidor]="errores.de('correo')"
            />
            <app-campo
              nombre="telefono"
              etiqueta="Teléfono"
              tipo="tel"
              placeholder="300 000 0000"
              [control]="form.controls.telefono"
              autocompletar="off"
              [errorServidor]="errores.de('telefono')"
            />
            @if (config.tipo === 'empleado') {
              <app-campo
                nombre="idRol"
                etiqueta="Cargo"
                tipo="select"
                opcionVacia="Selecciona un cargo"
                [opciones]="roles()"
                [control]="form.controls.idRol"
                [errorServidor]="errores.de('idRol')"
              />
            }
          </div>

          @if (errorGeneral(); as e) {
            <div class="aviso error" role="alert"><span aria-hidden="true">⚠ </span>{{ e }}</div>
          }

          <div class="acciones">
            <a class="boton secundario" [routerLink]="volverA()">Cancelar</a>
            <button type="submit" class="boton" [disabled]="guardando()">
              {{ guardando() ? 'Guardando…' : 'Guardar' }}
            </button>
          </div>
        </form>
      }
    </section>
  `,
  styles: `
    .formulario {
      display: flex;
      flex-direction: column;
      gap: 24px;
      padding: 28px 32px;
      max-width: 860px;
    }
    .rejilla {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 24px 28px;
    }
    .acciones {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
    .volver {
      margin-top: 8px;
    }
    @media (max-width: 768px) {
      .rejilla {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class FormularioPersonal implements OnInit {
  protected readonly config = configDeRuta();
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = apiDeTipo(this.config.tipo);
  private readonly empleadosApi = inject(EmpleadosApi);
  private readonly distribuidoresApi = inject(DistribuidoresApi);

  private readonly id = this.route.snapshot.paramMap.get('id');
  protected readonly editando = this.id !== null;

  protected readonly form = new FormGroup({
    nombre: new FormControl('', { nonNullable: true, validators: requerido }),
    documento: new FormControl('', { nonNullable: true, validators: requerido }),
    correo: new FormControl('', {
      nonNullable: true,
      validators: [...requerido, Validators.email],
    }),
    telefono: new FormControl('', { nonNullable: true, validators: [...requerido, telefono] }),
    idRol: new FormControl('', {
      nonNullable: true,
      validators: this.config.tipo === 'empleado' ? requerido : [],
    }),
  });
  protected readonly errores = new ErroresCampo([this.form]);

  protected readonly roles = signal<OpcionCampo[]>([]);
  protected readonly cargando = signal(this.editando || this.config.tipo === 'empleado');
  protected readonly noEncontrado = signal(false);
  protected readonly guardando = signal(false);
  protected readonly errorGeneral = signal<string | null>(null);

  protected volverA(): string {
    return this.editando ? `${this.config.ruta}/${this.id}` : this.config.ruta;
  }

  async ngOnInit(): Promise<void> {
    try {
      if (this.config.tipo === 'empleado') {
        const roles = await firstValueFrom(this.empleadosApi.roles());
        this.roles.set(roles.map((r) => ({ valor: String(r.id), etiqueta: r.titulo })));
      }
      if (this.editando) {
        const c = camposDeDetalle(await firstValueFrom(this.api.detalle(Number(this.id))));
        this.form.patchValue({
          nombre: c['nombre'] ?? '',
          documento: c['documento'] ?? '',
          correo: c['correo'] ?? '',
          telefono: c['telefono'] ?? '',
          idRol: c['idRol'] ?? '',
        });
        this.form.markAsPristine();
      }
    } catch (e) {
      const err = e as ErrorApi;
      if (err.estado === 404) this.noEncontrado.set(true);
      else this.errorGeneral.set(err.mensaje);
    } finally {
      this.cargando.set(false);
    }
  }

  protected async guardar(): Promise<void> {
    this.errorGeneral.set(null);
    this.errores.limpiar();
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.errorGeneral.set('Faltan campos obligatorios o tienen un formato incorrecto.');
      return;
    }
    this.guardando.set(true);
    try {
      const v = this.form.getRawValue();
      const base: DistribuidorDTO = {
        nombre: v.nombre.trim(),
        documento: v.documento.trim(),
        correo: v.correo.trim(),
        telefono: v.telefono.trim(),
      };
      const destino = await this.enviar(base, Number(v.idRol));
      await this.router.navigate([this.config.ruta, destino.id], {
        state: { aviso: destino.aviso },
      });
    } catch (e) {
      this.mostrarError(e as ErrorApi);
    } finally {
      this.guardando.set(false);
    }
  }

  private async enviar(
    base: DistribuidorDTO,
    idRol: number,
  ): Promise<{ id: number; aviso: string }> {
    if (this.config.tipo === 'empleado') {
      const datos: EmpleadoDTO = { ...base, idRol };
      if (this.editando) {
        await firstValueFrom(this.empleadosApi.modificar(Number(this.id), datos));
        return { id: Number(this.id), aviso: 'Los cambios del empleado se guardaron.' };
      }
      const r = await firstValueFrom(this.empleadosApi.crear(datos));
      return { id: r.id, aviso: 'Empleado creado.' };
    }
    if (this.editando) {
      await firstValueFrom(this.distribuidoresApi.modificar(Number(this.id), base));
      return { id: Number(this.id), aviso: 'Los cambios del distribuidor se guardaron.' };
    }
    const r = await firstValueFrom(this.distribuidoresApi.crear(base));
    return { id: r.id, aviso: `Distribuidor creado. Código asignado: ${r.codigo}.` };
  }

  private mostrarError(e: ErrorApi): void {
    const campo = campoDelError(e);
    if (campo && campo in this.form.controls) {
      this.errores.fijar(campo, e.mensaje);
      return;
    }
    if (e.estado === 404) {
      this.noEncontrado.set(true);
      return;
    }
    this.errorGeneral.set(e.mensaje);
  }
}
