import { Component, ViewChild, ElementRef, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ApiService, ChatResponse } from '../services/api.service';

interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: string[];
  duration_ms?: number;
  attempts?: number;
  timestamp: Date;
  feedbackGiven?: 'up' | 'down' | null;
  query?: string;
}

@Component({
  selector: 'app-chat',
  templateUrl: './chat.page.html',
  styleUrls: ['./chat.page.scss'],
  standalone: false,
})
export class ChatPage implements OnInit {
  @ViewChild('chatContent', { read: ElementRef }) chatContent!: ElementRef;

  useCases = [
    { key: 'engineering_docs', label: 'Engineering Docs' },
    { key: 'filter_design', label: 'Filter Design' },
  ];
  activeUseCase = 'engineering_docs';
  conversations: Record<string, ChatMessage[]> = {
    engineering_docs: [],
    filter_design: [],
  };

  inputText = '';
  isLoading = false;
  feedbackNotes = '';

  constructor(private api: ApiService, private route: ActivatedRoute) {}

  ngOnInit() {
    this.loadHistory();
    this.route.queryParams.subscribe((params) => {
      if (params['use_case'] && this.conversations[params['use_case']]) {
        this.activeUseCase = params['use_case'];
      }
      if (params['prompt']) {
        this.inputText = params['prompt'];
      }
    });
  }

  get messages(): ChatMessage[] {
    return this.conversations[this.activeUseCase];
  }

  switchUseCase(key: string) {
    this.activeUseCase = key;
  }

  sendMessage() {
    const text = this.inputText.trim();
    if (!text || this.isLoading) return;

    this.messages.push({ role: 'user', text, timestamp: new Date() });
    this.inputText = '';
    this.isLoading = true;
    this.scrollToBottom();

    this.api.chat(text, this.activeUseCase).subscribe({
      next: (res: ChatResponse) => {
        this.messages.push({
          role: 'assistant',
          text: res.response,
          sources: res.sources,
          duration_ms: res.duration_ms,
          attempts: res.attempts,
          timestamp: new Date(),
          feedbackGiven: null,
          query: text,
        });
        this.isLoading = false;
        this.saveHistory();
        this.scrollToBottom();
      },
      error: (err) => {
        this.messages.push({
          role: 'assistant',
          text: 'Error: ' + (err.error?.detail || err.message || 'Request failed'),
          timestamp: new Date(),
        });
        this.isLoading = false;
        this.scrollToBottom();
      },
    });
  }

  onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }

  giveFeedback(msg: ChatMessage, relevant: boolean) {
    msg.feedbackGiven = relevant ? 'up' : 'down';
    const sources = msg.sources || [];
    for (const docId of sources) {
      this.api.submitFeedback({
        query: msg.query || '',
        document_id: docId,
        relevant,
        score: 0,
        notes: this.feedbackNotes,
        use_case: this.activeUseCase,
      }).subscribe();
    }
  }

  clearChat() {
    this.conversations[this.activeUseCase] = [];
    this.saveHistory();
  }

  private saveHistory() {
    try {
      localStorage.setItem('chat_history', JSON.stringify(this.conversations));
    } catch { /* quota exceeded — ignore */ }
  }

  private loadHistory() {
    try {
      const saved = localStorage.getItem('chat_history');
      if (saved) {
        const parsed = JSON.parse(saved);
        for (const key of Object.keys(parsed)) {
          if (this.conversations[key]) {
            this.conversations[key] = parsed[key].map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp),
            }));
          }
        }
      }
    } catch { /* corrupted — ignore */ }
  }

  private scrollToBottom() {
    setTimeout(() => {
      if (this.chatContent?.nativeElement) {
        this.chatContent.nativeElement.scrollTop = this.chatContent.nativeElement.scrollHeight;
      }
    }, 100);
  }
}
