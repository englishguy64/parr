import { Component, inject, signal } from '@angular/core';
import { SurfaceComponent } from '@a2ui/angular/v0_9';
import { AgentService } from './agent.service';

@Component({
  imports: [SurfaceComponent],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {
  protected readonly agent = inject(AgentService);
  protected readonly prompt = signal('Give me three tips for a calm first day at a new job.');
}
