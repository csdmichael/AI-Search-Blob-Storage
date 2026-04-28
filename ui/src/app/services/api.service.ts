import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ChatResponse {
  prompt: string;
  response: string;
  use_case: string;
  duration_ms: number;
  sources: string[];
}

export interface BatchResultItem {
  prompt: string;
  response: string;
  duration_ms: number;
  sources: string[];
  passed: boolean;
  reason: string;
}

export interface BatchResponse {
  use_case: string;
  total: number;
  passed: number;
  failed: number;
  accuracy_pct: number;
  results: BatchResultItem[];
}

export interface SamplePrompt {
  text: string;
  category: string;
}

export interface PromptsMap {
  keyword: SamplePrompt[];
  semantic: SamplePrompt[];
  agent: SamplePrompt[];
}

export interface FeedbackRequest {
  query: string;
  document_id: string;
  relevant: boolean;
  score: number;
  notes: string;
  use_case: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getPrompts(useCase: string): Observable<PromptsMap> {
    return this.http.get<PromptsMap>(`${this.base}/prompts`, { params: { use_case: useCase } });
  }

  chat(prompt: string, useCase: string): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.base}/chat`, { prompt, use_case: useCase });
  }

  batchRun(prompts: string[], useCase: string): Observable<BatchResponse> {
    return this.http.post<BatchResponse>(`${this.base}/batch`, { prompts, use_case: useCase });
  }

  submitFeedback(req: FeedbackRequest): Observable<any> {
    return this.http.post(`${this.base}/feedback`, req);
  }

  getFeedback(useCase: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/feedback`, { params: { use_case: useCase } });
  }
}
