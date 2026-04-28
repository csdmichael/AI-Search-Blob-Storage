import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { ToastController } from '@ionic/angular';
import { ApiService, SamplePrompt, BatchResponse, BatchResultItem } from '../services/api.service';

interface SelectablePrompt extends SamplePrompt {
  selected: boolean;
}

@Component({
  selector: 'app-prompts',
  templateUrl: './prompts.page.html',
  styleUrls: ['./prompts.page.scss'],
  standalone: false,
})
export class PromptsPage implements OnInit {
  useCases = [
    { key: 'engineering_docs', label: 'Engineering Docs' },
    { key: 'filter_design', label: 'Filter Design' },
  ];
  activeUseCase = 'engineering_docs';

  categories = ['keyword', 'semantic', 'agent'];
  prompts: Record<string, SelectablePrompt[]> = { keyword: [], semantic: [], agent: [] };

  isRunning = false;
  batchResult: BatchResponse | null = null;
  runProgress = 0;
  runTotal = 0;

  constructor(
    private api: ApiService,
    private toast: ToastController,
    private router: Router,
  ) {}

  ngOnInit() {
    this.loadPrompts();
  }

  switchUseCase(key: string) {
    this.activeUseCase = key;
    this.batchResult = null;
    this.loadPrompts();
  }

  loadPrompts() {
    this.api.getPrompts(this.activeUseCase).subscribe((data) => {
      for (const cat of this.categories) {
        const items = (data as any)[cat] || [];
        this.prompts[cat] = items.map((p: SamplePrompt) => ({ ...p, selected: false }));
      }
    });
  }

  get selectedCount(): number {
    const all: SelectablePrompt[] = ([] as SelectablePrompt[]).concat(...Object.values(this.prompts));
    return all.filter((p) => p.selected).length;
  }

  get allSelected(): boolean {
    const all: SelectablePrompt[] = ([] as SelectablePrompt[]).concat(...Object.values(this.prompts));
    return all.length > 0 && all.every((p) => p.selected);
  }

  toggleAll(checked: boolean) {
    for (const cat of this.categories) {
      this.prompts[cat].forEach((p) => (p.selected = checked));
    }
  }

  selectCategory(cat: string, checked: boolean) {
    this.prompts[cat].forEach((p) => (p.selected = checked));
  }

  isCategorySelected(cat: string): boolean {
    const items = this.prompts[cat];
    return items.length > 0 && items.every((p) => p.selected);
  }

  async copyPrompt(text: string) {
    await navigator.clipboard.writeText(text);
    const t = await this.toast.create({ message: 'Copied!', duration: 1200, position: 'bottom', color: 'success' });
    t.present();
  }

  useInChat(text: string) {
    this.router.navigate(['/chat'], { queryParams: { prompt: text, use_case: this.activeUseCase } });
  }

  runSelected() {
    const selected: SelectablePrompt[] = ([] as SelectablePrompt[]).concat(...Object.values(this.prompts)).filter((p) => p.selected);
    if (selected.length === 0) return;

    this.isRunning = true;
    this.batchResult = null;
    this.runTotal = selected.length;
    this.runProgress = 0;

    const texts = selected.map((p) => p.text);

    this.api.batchRun(texts, this.activeUseCase).subscribe({
      next: (res: BatchResponse) => {
        this.batchResult = res;
        this.runProgress = res.total;
        this.isRunning = false;
      },
      error: () => {
        this.isRunning = false;
      },
    });
  }

  getResultColor(item: BatchResultItem): string {
    return item.passed ? 'success' : 'danger';
  }

  getAccuracyColor(pct: number): string {
    if (pct >= 90) return 'success';
    if (pct >= 70) return 'warning';
    return 'danger';
  }
}
