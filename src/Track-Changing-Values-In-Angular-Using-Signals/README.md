# Track Changing Values In Angular Using Signals

A small Angular SPA that shows how signals track changing values. It matches the Manim video.

| Part | What it shows |
| --- | --- |
| `ShoppingBasketService` | `signal()` holds the items, `computed()` derives count and total, `effect()` saves the total |
| `HeaderComponent` | Reads `count()` in its template |
| `ShoppingBasketComponent` | Reads `count()` and `total()` in its template |
| `ProductListComponent` | Calls `add()` but reads no signals, so it is not checked when the basket changes |

## Run

```
cd website
npm install
npm start
```

Open http://localhost:4200, press Add, and watch the browser console. Each component logs when Angular checks it.

Docs: https://angular.dev/guide/signals
