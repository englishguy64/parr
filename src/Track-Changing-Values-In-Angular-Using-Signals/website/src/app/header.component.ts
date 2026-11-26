import { ChangeDetectionStrategy, Component, DoCheck, inject } from '@angular/core';
import { ShoppingBasketService } from './shopping-basket.service';

@Component({
  selector: 'app-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<header>
    <h1>Track Changing Values In Angular Using Signals</h1>
    <span class="badge">Cart: {{ store.count() }}</span>
  </header>`,
  styles: `
    header { display: flex; justify-content: space-between; align-items: center; padding: 0.8rem 1rem;
      background: #fff; border: 2px solid #7a1f3d; border-radius: 8px; }
    h1 { margin: 0; font-size: 1.2rem; color: #7a1f3d; }
    .badge { font-weight: bold; color: #7a1f3d; }
  `,
})
export class HeaderComponent implements DoCheck {
  protected readonly store = inject(ShoppingBasketService);

  ngDoCheck(): void {
    console.log('HeaderComponent checked');
  }
}
