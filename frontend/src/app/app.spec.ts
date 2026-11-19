import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { ContingenciaStore } from './core/contingencia.store';

describe('App', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  it('no muestra el banner de contingencia por defecto', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('.banner')).toBeNull();
  });

  it('muestra el banner cuando hay contingencia', async () => {
    TestBed.inject(ContingenciaStore).activar();
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('.banner')?.textContent).toContain(
      'modo contingencia',
    );
  });
});
