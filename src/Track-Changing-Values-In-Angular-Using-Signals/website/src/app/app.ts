import { ChangeDetectionStrategy, Component } from '@angular/core';
import { HeaderComponent } from './header.component';
import { ProductListComponent } from './product-list.component';
import { ShoppingBasketComponent } from './shopping-basket.component';

@Component({
  selector: 'app-root',
  imports: [HeaderComponent, ProductListComponent, ShoppingBasketComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<main>
    <app-header />
    <div class="row">
      <app-product-list />
      <app-shopping-basket />
    </div>
  </main>`,
  styles: `
    main { max-width: 760px; margin: 1.5rem auto; display: grid; gap: 1rem; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
  `,
})
export class App {}
