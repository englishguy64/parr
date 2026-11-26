import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { BasicCatalog, provideA2Ui, provideMarkdownRenderer } from '@a2ui/angular/v0_9';
import { renderMarkdown } from '@a2ui/markdown-it';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // The A2UI renderer. The Basic catalog gives us Text, Card, Column, Button, Divider and more.
    provideA2Ui({ catalogs: [new BasicCatalog()] }),
    provideMarkdownRenderer(renderMarkdown),
  ],
};
