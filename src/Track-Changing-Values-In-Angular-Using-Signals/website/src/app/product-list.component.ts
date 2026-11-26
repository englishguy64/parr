import { ChangeDetectionStrategy, Component, DoCheck, inject } from '@angular/core';
import { Item, ShoppingBasketService } from './shopping-basket.service';

@Component({
  selector: 'app-product-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<section>
    <h2>ProductListComponent</h2>
    @for (product of products; track product.name) {
      <p>
        <span>{{ product.name }} {{ product.price }}</span>
        <button type="button" (click)="store.add(product)">Add</button>
      </p>
    }
    <small>This template reads no signals, so Angular does not check it when the basket changes.</small>
  </section>`,
  styles: `
    section { background: #fff; border: 2px solid #7a1f3d; border-radius: 8px; padding: 0.8rem 1rem; }
    h2 { margin: 0 0 0.6rem; font-size: 1rem; color: #7a1f3d; }
    p { display: flex; justify-content: space-between; align-items: center; margin: 0.6rem 0; }
    small { color: #6b7280; }
  `,
})
export class ProductListComponent implements DoCheck {
  protected readonly store = inject(ShoppingBasketService);
  protected readonly products: Item[] = [
    { name: 'Book', price: 19 },
    { name: 'Pen', price: 7 },
  ];

  ngDoCheck(): void {
    console.log('ProductListComponent checked');
  }
}
