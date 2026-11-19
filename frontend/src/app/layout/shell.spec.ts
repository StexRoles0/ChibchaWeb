import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { USUARIOS_SIMULADOS, UsuarioSimulado } from '../core/api/simulado/sesiones';
import { SesionStore } from '../core/auth/sesion.store';
import { Shell } from './shell';

async function render(usuario: UsuarioSimulado) {
  TestBed.configureTestingModule({ providers: [provideRouter([])] });
  TestBed.inject(SesionStore).establecer(USUARIOS_SIMULADOS[usuario]);
  const fixture = TestBed.createComponent(Shell);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  return {
    el,
    menu: Array.from(el.querySelectorAll('nav a')).map((a) => a.textContent?.trim()),
  };
}

describe('Shell', () => {
  it('menú de cliente', async () => {
    const { menu, el } = await render('cliente');
    expect(menu).toEqual(['Inicio', 'Mi perfil', 'Dominios', 'Soporte']);
    expect(el.querySelector('.rol')?.textContent).toContain('Cliente');
    expect(el.querySelector('.avatar')?.textContent).toBe('SN');
  });

  it('menú de gestión', async () => {
    expect((await render('gestion')).menu).toEqual([
      'Inicio',
      'Empleados',
      'Distribuidores',
      'Clientes',
      'Reportar novedad',
    ]);
  });

  it('menú de soporte', async () => {
    expect((await render('soporte')).menu).toEqual(['Bandeja de tickets', 'Reportar novedad']);
  });

  it('menú de administrador', async () => {
    expect((await render('admin')).menu).toEqual([
      'Inicio',
      'Migración',
      'Contingencia',
      'Reportar novedad',
    ]);
  });

  it('oculta ítems cuya operación no tiene la sesión', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    TestBed.inject(SesionStore).establecer({
      ...USUARIOS_SIMULADOS.gestion!,
      operaciones: ['CONSULTAR_REGISTROS'],
    });
    const fixture = TestBed.createComponent(Shell);
    await fixture.whenStable();
    const menu = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('nav a')).map(
      (a) => a.textContent?.trim(),
    );
    expect(menu).toEqual(['Clientes', 'Reportar novedad']);
  });
});
