import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({ name: 'formatResponse', standalone: false })
export class FormatResponsePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(text: string, useCase?: string): SafeHtml {
    if (!text) return '';

    const useCaseQuery = useCase ? `?use_case=${encodeURIComponent(useCase)}` : '';

    let html = text
      // Escape HTML
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Bold **text**
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Citations [source†index] — make clickable links to document viewer
      .replace(
        /\[([^\[\]†]+?)†([^\[\]]+?)\]/g,
        (_match: string, source: string, _index: string) => {
          const docId = source.replace(/\.(txt|json|pdf|pptx?)$/i, '');
          const encodedDocId = encodeURIComponent(docId);
          return `<a class="citation" href="/documents/${encodedDocId}${useCaseQuery}" title="View ${source}" target="_blank" rel="noopener noreferrer">${source}</a>`;
        },
      )
      // Line breaks
      .replace(/\n/g, '<br>');

    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}
