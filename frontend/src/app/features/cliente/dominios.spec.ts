import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { DominiosApi } from '../../core/api/dominios.api';
import { ResumenDTO } from '../../core/api/dto';
import { Dominios } from './dominios';

const FILAS: ResumenDTO[] = [
  { id: 3, titulo: 'cafedeboyaca.net', subtitulo: '2026-10-28', estado: 'REGISTRADA' },
  { id: 2, titulo: 'tostadoresboyaca.co', subtitulo: '2026-10-02', estado: 'FALLIDA' },
  { id: 1, titulo: 'cafedeboyaca.com', subtitulo: '2026-09-14', estado: 'ENVIADA' },
];

const el = (f: { nativeElement: unknown }) => f.nativeElement as HTMLElement;
const escribir = (e: HTMLInputElement | HTMLSelectElement, v: string) => {
  e.value = v;
  e.dispatchEvent(new Event(e instanceof HTMLSelectElement ? 'change' : 'input'));
};

async function montar(api: Partial<DominiosApi>) {
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    providers: [provideRouter([]), { provide: DominiosApi, useValue: api }],
  });
  const f = TestBed.createComponent(Dominios);
  await f.whenStable();
  return f;
}

const enviar = async (f: Awaited<ReturnType<typeof montar>>) => {
  el(f).querySelector('form')!.dispatchEvent(new Event('submit'));
  await f.whenStable();
};

describe('M-09 Dominios', () => {
  it('muestra título, formulario y el historial con la etiqueta de cada estado', async () => {
    const f = await montar({ solicitudes: () => of(FILAS) });
    const t = el(f).textContent!;
    expect(t).toContain('Solicitar un dominio');
    expect(t).toContain('Nueva solicitud');
    expect(t).toContain('Solicitudes enviadas');
    expect(el(f).querySelector('label[for="nombre"]')).not.toBeNull();
    const filas = Array.from(el(f).querySelectorAll('tbody tr')).map((r) =>
      r.textContent!.replace(/\s+/g, ' ').trim(),
    );
    expect(filas[0]).toBe('cafedeboyaca.net 28/10/2026 Registrada');
    expect(filas[1]).toContain('Fallida');
    expect(filas[2]).toContain('Enviada al registrador');
    expect(
      Array.from(el(f).querySelectorAll('select#extension option')).map((o) => o.textContent),
    ).toEqual(['.com', '.co', '.net', '.org']);
  });

  it('sin solicitudes muestra el estado vacío y sin fecha en el servidor omite la columna', async () => {
    const f = await montar({ solicitudes: () => of([]) });
    expect(el(f).textContent).toContain('Aún no has solicitado ningún dominio.');
    const g = await montar({
      solicitudes: () => of([{ id: 1, titulo: 'a.com', subtitulo: '', estado: 'ENVIADA' }]),
    });
    expect(Array.from(el(g).querySelectorAll('th')).map((h) => h.textContent!.trim())).toEqual([
      'Dominio',
      'Estado',
    ]);
  });

  it('el aviso de formato válido sale mientras se escribe y desaparece si es inválido', async () => {
    const f = await montar({ solicitudes: () => of([]) });
    const nombre = el(f).querySelector<HTMLInputElement>('#nombre')!;
    escribir(nombre, 'Cafe-de-Boyaca');
    escribir(el(f).querySelector<HTMLSelectElement>('#extension')!, '.co');
    await f.whenStable();
    expect(el(f).textContent).toContain('cafe-de-boyaca.co tiene un formato válido.');
    escribir(nombre, '-cafe');
    await f.whenStable();
    expect(el(f).textContent).not.toContain('tiene un formato válido');
  });

  it('RN-16: guion inicial o 64 caracteres muestran el error bajo el campo y no llaman al servicio', async () => {
    const solicitar = vi.fn();
    const f = await montar({ solicitudes: () => of([]), solicitar });
    const nombre = el(f).querySelector<HTMLInputElement>('#nombre')!;
    escribir(nombre, '-cafe');
    await enviar(f);
    expect(el(f).querySelector('#nombre-error')?.textContent).toContain('sin guion');
    escribir(nombre, 'a'.repeat(64));
    await enviar(f);
    expect(el(f).querySelector('#nombre-error')?.textContent).toContain('63');
    escribir(nombre, '');
    await enviar(f);
    expect(el(f).querySelector('#nombre-error')?.textContent).toContain('obligatorio');
    expect(solicitar).not.toHaveBeenCalled();
  });

  it('envía nombre en minúsculas y extensión, recarga la tabla y confirma el envío', async () => {
    const solicitar = vi.fn(() => of({ id: 9, estado: 'ENVIADA' }));
    const solicitudes = vi.fn(() => of(FILAS));
    const f = await montar({ solicitudes, solicitar });
    escribir(el(f).querySelector<HTMLInputElement>('#nombre')!, 'Mi-Tienda');
    escribir(el(f).querySelector<HTMLSelectElement>('#extension')!, '.org');
    await enviar(f);
    expect(solicitar).toHaveBeenCalledWith({ nombre: 'mi-tienda', extension: '.org' });
    expect(solicitudes).toHaveBeenCalledTimes(2);
    expect(el(f).querySelector('.aviso.exito')?.textContent).toContain('mi-tienda.org enviada');
    expect(el(f).querySelector<HTMLInputElement>('#nombre')!.value).toBe('');
  });

  it('registrador que rechaza: la respuesta 201 FALLIDA se ve como advertencia y conserva el nombre', async () => {
    const f = await montar({
      solicitudes: () => of(FILAS),
      solicitar: () => of({ id: 9, estado: 'FALLIDA' }),
    });
    escribir(el(f).querySelector<HTMLInputElement>('#nombre')!, 'tienda-rechazo');
    await enviar(f);
    const a = el(f).querySelector('.aviso.advertencia')!;
    expect(a.textContent).toContain('tienda-rechazo.com');
    expect(a.textContent).toContain('solicitud nueva');
    expect(el(f).querySelector<HTMLInputElement>('#nombre')!.value).toBe('tienda-rechazo');
  });

  it('422 del servidor sale debajo del campo que indica `campo`; otros errores en el aviso', async () => {
    let error: unknown = {
      estado: 422,
      codigo: 'VALIDACION',
      campo: 'extension',
      mensaje: 'La extensión no está admitida.',
    };
    const f = await montar({
      solicitudes: () => of([]),
      solicitar: () => throwError(() => error),
    });
    escribir(el(f).querySelector<HTMLInputElement>('#nombre')!, 'tienda');
    await enviar(f);
    expect(el(f).querySelector('#extension-error')?.textContent).toContain('no está admitida');
    error = { estado: 500, codigo: 'ERROR', mensaje: 'Ocurrió un error inesperado.' };
    await enviar(f);
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('error inesperado');
  });

  it('503 CONTINGENCIA no duplica el mensaje: lo muestra el banner global', async () => {
    const f = await montar({
      solicitudes: () => of([]),
      solicitar: () =>
        throwError(() => ({ estado: 503, codigo: 'CONTINGENCIA', mensaje: 'contingencia' })),
    });
    escribir(el(f).querySelector<HTMLInputElement>('#nombre')!, 'tienda');
    await enviar(f);
    expect(el(f).querySelector('.aviso.error')).toBeNull();
    expect(el(f).querySelector<HTMLButtonElement>('button[type="submit"]')!.disabled).toBe(false);
  });

  it('si el historial falla ofrece Reintentar', async () => {
    let falla = true;
    const f = await montar({
      solicitudes: () => (falla ? throwError(() => ({ mensaje: 'Sin conexión.' })) : of(FILAS)),
    });
    expect(el(f).querySelector('.aviso.error')?.textContent).toContain('Sin conexión.');
    falla = false;
    el(f).querySelector<HTMLButtonElement>('.aviso.error button')!.click();
    await f.whenStable();
    expect(el(f).querySelectorAll('tbody tr').length).toBe(3);
  });
});
