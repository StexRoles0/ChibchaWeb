import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { BannerContingencia } from './layout/banner-contingencia';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, BannerContingencia],
  template: `
    <app-banner-contingencia />
    <router-outlet />
  `,
})
export class App {}
