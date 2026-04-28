import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';

interface HistoryEntry {
  role: string;
  text: string;
  sources?: string[];
  duration_ms?: number;
  attempts?: number;
  timestamp: string;
  feedbackGiven?: string | null;
  query?: string;
}

interface FeedbackEntry {
  timestamp: string;
  query: string;
  document_id: string;
  relevant: boolean;
  search_score: number;
  notes: string;
}

@Component({
  selector: 'app-history',
  templateUrl: './history.page.html',
  styleUrls: ['./history.page.scss'],
  standalone: false,
})
export class HistoryPage implements OnInit {
  useCases = [
    { key: 'engineering_docs', label: 'Engineering Docs' },
    { key: 'filter_design', label: 'Filter Design' },
  ];
  activeUseCase = 'engineering_docs';
  activeTab = 'conversations';

  conversations: HistoryEntry[] = [];
  feedback: FeedbackEntry[] = [];

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.loadAll();
  }

  switchUseCase(key: string) {
    this.activeUseCase = key;
    this.loadAll();
  }

  loadAll() {
    this.loadConversations();
    this.loadFeedback();
  }

  loadConversations() {
    try {
      const saved = localStorage.getItem('chat_history');
      if (saved) {
        const parsed = JSON.parse(saved);
        this.conversations = (parsed[this.activeUseCase] || []).filter(
          (m: HistoryEntry) => m.role === 'assistant'
        );
      } else {
        this.conversations = [];
      }
    } catch {
      this.conversations = [];
    }
  }

  loadFeedback() {
    this.api.getFeedback(this.activeUseCase).subscribe({
      next: (data) => { this.feedback = data; },
      error: () => { this.feedback = []; },
    });
  }

  getFeedbackIcon(entry: HistoryEntry): string {
    if (entry.feedbackGiven === 'up') return 'thumbs-up';
    if (entry.feedbackGiven === 'down') return 'thumbs-down';
    return 'remove-outline';
  }

  getFeedbackColor(entry: HistoryEntry): string {
    if (entry.feedbackGiven === 'up') return 'success';
    if (entry.feedbackGiven === 'down') return 'danger';
    return 'medium';
  }

  clearHistory() {
    localStorage.removeItem('chat_history');
    this.conversations = [];
  }

  get positiveFeedbackCount(): number {
    return this.feedback.filter((f) => f.relevant).length;
  }

  get negativeFeedbackCount(): number {
    return this.feedback.filter((f) => !f.relevant).length;
  }
}
