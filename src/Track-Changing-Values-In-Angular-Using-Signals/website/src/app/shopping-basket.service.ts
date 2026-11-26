import { Injectable, computed, effect, signal } from '@angular/core';

export interface Item {
  name: string;
  price: number;
}

const STORAGE_KEY = 'shopping-basket-total';

/** The store. One writable signal, two computed signals and one effect. */
@Injectable({ providedIn: 'root' })
export class ShoppingBasketService {
  /** signal(): a writable value that tells Angular who reads it. */
  readonly items = signal<Item[]>([]);

  /** computed(): derived, read-only and cached until items changes. */
  readonly count = computed(() => this.items().length);
  readonly total = computed(() => this.items().reduce((sum, item) => sum + item.price, 0));

  constructor() {
    // effect(): a side effect that runs again whenever a signal it reads changes.
    effect(() => {
      const total = this.total();
      localStorage.setItem(STORAGE_KEY, String(total));
      console.log(`effect: saved total ${total}`);
    });
  }

  add(item: Item): void {
    this.items.update((items) => [...items, item]);
  }

  clear(): void {
    this.items.set([]);
  }
}
