import { ChangeDetectionStrategy, Component, DoCheck, inject } from '@angular/core';
import { ShoppingBasketService } from './shopping-basket.service';

@Component({
  selector: 'app-shopping-basket',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<section>
    <h2>ShoppingBasketComponent</h2>
    <p>Items: {{ store.count() }}</p>
    <p>Total: {{ store.total() }}</p>
    <button type="button" (click)="store.clear()" [disabled]="store.count() === 0">Clear</button>
  </section>`,
  styles: `
    section { background: #fff; border: 2px solid #7a1f3d; border-radius: 8px; padding: 0.8rem 1rem; }
    h2 { margin: 0 0 0.6rem; font-size: 1rem; color: #7a1f3d; }
    p { font-size: 1.1rem; font-weight: bold; margin: 0.4rem 0; }
  `,
})
export class ShoppingBasketComponent implements DoCheck {
  protected readonly store = inject(ShoppingBasketService);

  ngDoCheck(): void {
    console.log('ShoppingBasketComponent checked');
  }
}
