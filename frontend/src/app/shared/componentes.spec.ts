import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { FormControl, Validators } from '@angular/forms';
import { Campo } from './campo';
import { DialogoConfirmacion } from './dialogo-confirmacion';
import { EtiquetaEstado } from './etiqueta-estado';
import { ErroresCampo, campoDelError } from './errores-formulario';
import { FormGroup } from '@angular/forms';

describe('Campo', () => {
  async function crear(control: FormControl<string>, errorServidor: string | null = null) {
    const f = TestBed.createComponent(Campo);
    f.componentRef.setInput('control', control);
    f.componentRef.setInput('nombre', 'telefono');
    f.componentRef.setInput('etiqueta', 'Teléfono');
    f.componentRef.setInput('errorServidor', errorServidor);
    await f.whenStable();
    return f;
  }
  const el = (f: { nativeElement: unknown }) => f.nativeElement as HTMLElement;

  it('label asociado con for/id y sin error al inicio', async () => {
    const f = await crear(
      new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    );
    expect(el(f).querySelector('label')?.getAttribute('for')).toBe('telefono');
    expect(el(f).querySelector('input')?.id).toBe('telefono');
    expect(el(f).querySelector('.error')).toBeNull();
  });

  it('muestra el error de validación al tocar el campo y lo enlaza con aria-describedby', async () => {
    const c = new FormControl('', { nonNullable: true, validators: [Validators.required] });
    const f = await crear(c);
    c.markAsTouched();
    await f.whenStable();
    expect(el(f).querySelector('.error')?.textContent).toContain('obligatorio');
    const input = el(f).querySelector('input')!;
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.getAttribute('aria-describedby')).toBe('telefono-error');
  });

  it('muestra el error 422 del servidor debajo del campo aunque no esté tocado', async () => {
    const f = await crear(
      new FormControl('3001234567', { nonNullable: true }),
      'Teléfono no válido',
    );
    expect(el(f).querySelector('.error')?.textContent).toContain('Teléfono no válido');
  });
});

describe('ErroresCampo (422 por campo)', () => {
  it('guarda el mensaje por campo y lo borra cuando el usuario edita ese campo', () => {
    TestBed.runInInjectionContext(() => {
      const form = new FormGroup({ sitio: new FormControl(''), telefono: new FormControl('') });
      const e = new ErroresCampo([form]);
      e.fijar('sitio', 'En uso');
      e.fijar('telefono', 'Inválido');
      expect(e.de('sitio')).toBe('En uso');
      form.controls.sitio.setValue('otro');
      expect(e.de('sitio')).toBeNull();
      expect(e.de('telefono')).toBe('Inválido');
      e.limpiar();
      expect(e.errores()).toEqual({});
    });
  });

  it('campoDelError: 422 usa `campo`; SUBDOMINIO_EN_USO apunta a sitio; otros no tienen campo', () => {
    expect(
      campoDelError({ estado: 422, codigo: 'VALIDACION', mensaje: '', campo: 'vencimiento' }),
    ).toBe('vencimiento');
    expect(campoDelError({ estado: 409, codigo: 'SUBDOMINIO_EN_USO', mensaje: '' })).toBe('sitio');
    expect(campoDelError({ estado: 500, codigo: 'ERROR', mensaje: '' })).toBeUndefined();
  });
});

describe('EtiquetaEstado', () => {
  it('lleva texto además de color', async () => {
    const f = TestBed.createComponent(EtiquetaEstado);
    f.componentRef.setInput('estado', 'ESCALADO');
    await f.whenStable();
    const span = (f.nativeElement as HTMLElement).querySelector('.etiqueta')!;
    expect(span.textContent).toBe('Escalado');
    expect(span.classList.contains('oro')).toBe(true);
  });
});

@Component({
  imports: [DialogoConfirmacion],
  template: `
    <button id="abre">abre</button>
    <app-dialogo-confirmacion
      titulo="Eliminar"
      (cancelar)="cancelado = true"
      (confirmar)="confirmado = true"
    >
      <input id="dentro" data-foco-inicial />
    </app-dialogo-confirmacion>
  `,
})
class Anfitrion {
  cancelado = false;
  confirmado = false;
}

describe('DialogoConfirmacion', () => {
  it('enfoca el campo inicial, atrapa el foco con Tab y cancela con Escape', async () => {
    const f = TestBed.createComponent(Anfitrion);
    document.body.appendChild(f.nativeElement);
    await f.whenStable();
    const raiz = f.nativeElement as HTMLElement;
    const dialogo = raiz.querySelector<HTMLElement>('[role="dialog"]')!;
    expect(dialogo.getAttribute('aria-modal')).toBe('true');
    expect(document.activeElement?.id).toBe('dentro');

    const botones = Array.from(dialogo.querySelectorAll<HTMLElement>('button'));
    const ultimo = botones[botones.length - 1];
    // el botón confirmar está habilitado: el último enfocable es "Confirmar"
    ultimo.focus();
    const tab = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    dialogo.dispatchEvent(tab);
    expect(tab.defaultPrevented).toBe(true);
    expect(document.activeElement?.id).toBe('dentro');

    const shiftTab = new KeyboardEvent('keydown', {
      key: 'Tab',
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    dialogo.dispatchEvent(shiftTab);
    expect(document.activeElement).toBe(ultimo);

    dialogo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    expect(f.componentInstance.cancelado).toBe(true);
    f.nativeElement.remove();
  });
});
