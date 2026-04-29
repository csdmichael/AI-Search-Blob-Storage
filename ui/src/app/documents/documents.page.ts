import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { ApiService, DocumentEntry, DocumentDetail } from '../services/api.service';
import { UseCaseService } from '../services/use-case.service';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

@Component({
  selector: 'app-documents',
  templateUrl: './documents.page.html',
  styleUrls: ['./documents.page.scss'],
  standalone: false,
})
export class DocumentsPage implements OnInit, OnDestroy {
  documents: DocumentEntry[] = [];
  filteredDocs: DocumentEntry[] = [];
  searchText = '';
  filterType = 'all';
  availableTypes: string[] = [];
  isLoading = false;

  // Detail view
  selectedDoc: DocumentDetail | null = null;
  selectedDocId = '';
  pdfUrl: SafeResourceUrl | null = null;

  private ucSub!: Subscription;

  constructor(
    public uc: UseCaseService,
    private api: ApiService,
    private route: ActivatedRoute,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit() {
    this.route.params.subscribe((params) => {
      this.selectedDocId = params['docId'] || '';
    });
    this.route.queryParams.subscribe((qp) => {
      if (qp['use_case']) { this.uc.switch(qp['use_case']); }
    });
    this.ucSub = this.uc.active$.subscribe(() => {
      this.selectedDoc = null;
      this.pdfUrl = null;
      this.filterType = 'all';
      this.loadDocuments();
    });
  }

  ngOnDestroy() { if (this.ucSub) this.ucSub.unsubscribe(); }

  loadDocuments() {
    this.isLoading = true;
    this.api.listDocuments(this.uc.activeKey).subscribe({
      next: (res) => {
        this.documents = res.documents;
        // Compute available types
        const types = new Set(this.documents.map((d) => d.type));
        this.availableTypes = Array.from(types).sort();
        this.applyFilter();
        this.isLoading = false;
        if (this.selectedDocId) { this.openDocument(this.selectedDocId); }
      },
      error: () => { this.isLoading = false; },
    });
  }

  applyFilter() {
    let docs = this.documents;
    if (this.filterType !== 'all') {
      docs = docs.filter((d) => d.type === this.filterType);
    }
    if (this.searchText.trim()) {
      const q = this.searchText.toLowerCase();
      docs = docs.filter((d) =>
        d.filename.toLowerCase().includes(q) ||
        (d.title || '').toLowerCase().includes(q) ||
        (d.status || '').toLowerCase().includes(q)
      );
    }
    this.filteredDocs = docs;
  }

  openDocument(docId: string) {
    this.selectedDocId = docId;
    this.pdfUrl = null;
    this.selectedDoc = null;

    // Check if this use case has PDFs and the specific document is not JSON
    const entry = this.documents.find((d) => d.doc_id === docId);
    if (this.uc.active.fileFormat === 'pdf' && entry?.type !== 'json') {
      // Show the actual PDF via iframe
      const url = this.api.getPdfUrl(docId, this.uc.activeKey);
      this.pdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(url);
    }

    // Also load JSON metadata
    this.api.getDocument(docId, this.uc.activeKey).subscribe({
      next: (doc) => { this.selectedDoc = doc; },
      error: () => { /* PDF-only doc, no JSON — that's OK */ },
    });
  }

  closeDocument() {
    this.selectedDoc = null;
    this.selectedDocId = '';
    this.pdfUrl = null;
  }

  getStatusColor(status: string): string {
    if (!status) return 'medium';
    const s = status.toUpperCase();
    if (s === 'PASS') return 'success';
    if (s === 'FAIL') return 'danger';
    if (s.includes('CONDITIONAL')) return 'warning';
    return 'medium';
  }

  getTypeIcon(type: string): string {
    if (type === 'json') return 'code-slash-outline';
    if (type === 'txt') return 'document-text-outline';
    if (type === 'pdf') return 'document-outline';
    return 'document-outline';
  }

  getSectionKeys(content: any): string[] {
    return Object.keys(content.sections || {});
  }

  getSectionLabel(key: string): string {
    return key.replace(/_/g, ' ').replace(/^\d+\s*/, (m: string) => m + '. ');
  }

  formatKey(key: string): string {
    return key.replace(/_/g, ' ');
  }
}
