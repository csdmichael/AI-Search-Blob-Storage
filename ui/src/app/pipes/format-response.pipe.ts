import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({ name: 'formatResponse', standalone: false })
export class FormatResponsePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(text: string): SafeHtml {
    if (!text) return '';

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
          // Strip file extension from source for doc_id routing
          const docId = source.replace(/\.(txt|json|pdf|pptx?)$/i, '');
          const encodedDocId = encodeURIComponent(docId);
          return `<a class="citation" href="/documents/${encodedDocId}" title="View ${source}">${source}</a>`;
        },
      )
      // Line breaks
      .replace(/\n/g, '<br>');

    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}
