import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
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
  loadError = '';

  // Detail view
  selectedDoc: DocumentDetail | null = null;
  selectedDocId = '';
  pdfUrl: SafeResourceUrl | null = null;
  originalText: string | null = null;
  viewerType: 'pdf' | 'office' | 'google' | 'text' | null = null;
  jsonTab: 'parsed' | 'raw' = 'parsed';

  private readonly originalTypeByUseCase: Record<string, string> = {
    engineering_docs: 'txt',
    filter_design: 'pdf',
    tax_pdf_forms: 'pdf',
    eng_design_ppt: 'pptx',
  };

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
      this.originalText = null;
      this.viewerType = null;
      this.filterType = 'all';
      this.loadDocuments();
    });
  }

  ngOnDestroy() { if (this.ucSub) this.ucSub.unsubscribe(); }

  loadDocuments() {
    this.isLoading = true;
    this.loadError = '';
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
      error: (err: HttpErrorResponse) => {
        this.documents = [];
        this.filteredDocs = [];
        this.availableTypes = [];
        this.loadError = this.extractApiError(err);
        this.isLoading = false;
      },
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
        (d.status || '').toLowerCase().includes(q) ||
        (d.state || '').toLowerCase().includes(q)
      );
    }
    this.filteredDocs = docs;
  }

  openDocument(docId: string) {
    this.selectedDocId = docId;
    this.pdfUrl = null;
    this.originalText = null;
    this.viewerType = null;
    this.selectedDoc = null;
    this.jsonTab = 'parsed';

    const entry = this.documents.find((d) => d.doc_id === docId);
    const originalType = this.getOriginalDocumentType(entry);

    if (originalType === 'pdf') {
      const fileUrl = this.api.getDocumentFileUrl(docId, this.uc.activeKey);
      const viewerUrl = this.getGooglePdfViewerUrl(fileUrl) ?? fileUrl;
      this.viewerType = this.getGooglePdfViewerUrl(fileUrl) ? 'google' : 'pdf';
      this.pdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(viewerUrl);
    } else if (originalType === 'pptx' || originalType === 'ppt') {
      const fileUrl = this.api.getDocumentFileUrl(docId, this.uc.activeKey);
      const officeViewerUrl = this.getOfficeViewerUrl(fileUrl);
      const viewerUrl = officeViewerUrl ?? fileUrl;
      this.viewerType = officeViewerUrl ? 'office' : 'pdf';
      this.pdfUrl = this.sanitizer.bypassSecurityTrustResourceUrl(viewerUrl);
    } else if (originalType === 'txt') {
      this.viewerType = 'text';
      this.api.getDocumentFileText(docId, this.uc.activeKey).subscribe({
        next: (content) => { this.originalText = content; },
        error: () => { this.originalText = 'Unable to load original text document.'; },
      });
    }

    // Also load JSON/text metadata
    this.api.getDocument(docId, this.uc.activeKey).subscribe({
      next: (doc) => { this.selectedDoc = doc; },
      error: () => { /* PDF-only doc, no JSON — that's OK */ },
    });
  }

  closeDocument() {
    this.selectedDoc = null;
    this.selectedDocId = '';
    this.pdfUrl = null;
    this.originalText = null;
    this.viewerType = null;
  }

  private getOriginalDocumentType(entry?: DocumentEntry): string | null {
    return this.originalTypeByUseCase[this.uc.activeKey] || entry?.type || null;
  }

  private getOfficeViewerUrl(fileUrl: string): string | null {
    try {
      const parsed = new URL(fileUrl);
      if (parsed.protocol !== 'https:' || parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
        return null;
      }
      return `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(fileUrl)}`;
    } catch {
      return null;
    }
  }

  private getGooglePdfViewerUrl(fileUrl: string): string | null {
    try {
      const parsed = new URL(fileUrl);
      if (parsed.protocol !== 'https:' || parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') {
        return null;
      }
      return `https://docs.google.com/gview?embedded=1&url=${encodeURIComponent(fileUrl)}`;
    } catch {
      return null;
    }
  }

  getStatusColor(status: string): string {
    if (!status) return 'medium';
    const s = status.toUpperCase();
    if (s === 'PASS') return 'success';
    if (s === 'FAIL') return 'danger';
    if (s.includes('CONDITIONAL')) return 'warning';
    if (s === 'EXTRACTED') return 'success';
    return 'medium';
  }

  getConfidenceColor(confidence: string): string {
    if (!confidence) return 'medium';
    const c = confidence.toUpperCase();
    if (c === 'HIGH') return 'success';
    if (c === 'MEDIUM') return 'warning';
    if (c === 'LOW') return 'danger';
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

  private extractApiError(err: HttpErrorResponse): string {
    const apiDetail = typeof err?.error?.detail === 'string' ? err.error.detail : '';
    if (apiDetail) {
      return apiDetail;
    }

    if (typeof err?.error === 'string' && err.error.trim()) {
      return err.error;
    }

    if (err?.status) {
      return `Document API request failed (${err.status} ${err.statusText || 'Error'}).`;
    }

    return 'Document API request failed. Please check API connectivity and configuration.';
  }
}
