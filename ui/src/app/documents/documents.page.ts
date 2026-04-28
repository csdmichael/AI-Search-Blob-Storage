import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, DocumentEntry, DocumentDetail } from '../services/api.service';

@Component({
  selector: 'app-documents',
  templateUrl: './documents.page.html',
  styleUrls: ['./documents.page.scss'],
  standalone: false,
})
export class DocumentsPage implements OnInit {
  useCases = [
    { key: 'engineering_docs', label: 'Engineering Docs' },
    { key: 'filter_design', label: 'Filter Design' },
  ];
  activeUseCase = 'engineering_docs';
  documents: DocumentEntry[] = [];
  filteredDocs: DocumentEntry[] = [];
  searchText = '';
  filterType = 'all';
  isLoading = false;

  // Detail view
  selectedDoc: DocumentDetail | null = null;
  selectedDocId = '';

  constructor(private api: ApiService, private route: ActivatedRoute) {}

  ngOnInit() {
    this.route.params.subscribe((params) => {
      if (params['docId']) {
        this.selectedDocId = params['docId'];
      }
    });
    this.route.queryParams.subscribe((params) => {
      if (params['use_case']) {
        this.activeUseCase = params['use_case'];
      }
      this.loadDocuments();
    });
  }

  switchUseCase(key: string) {
    this.activeUseCase = key;
    this.selectedDoc = null;
    this.selectedDocId = '';
    this.loadDocuments();
  }

  loadDocuments() {
    this.isLoading = true;
    this.api.listDocuments(this.activeUseCase).subscribe({
      next: (res) => {
        this.documents = res.documents;
        this.applyFilter();
        this.isLoading = false;
        if (this.selectedDocId) {
          this.openDocument(this.selectedDocId);
        }
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
    this.api.getDocument(docId, this.activeUseCase).subscribe({
      next: (doc) => { this.selectedDoc = doc; },
      error: () => { this.selectedDoc = null; },
    });
  }

  closeDocument() {
    this.selectedDoc = null;
    this.selectedDocId = '';
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
    return key.replace(/_/g, ' ').replace(/^\d+\s*/, (m) => m + '. ');
  }

  formatKey(key: string): string {
    return key.replace(/_/g, ' ');
  }
}
