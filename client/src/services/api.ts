/**
 * API Service for IP-SAKTI Sahayak
 * Handles all API calls to the backend
 */

export interface ChatRequest {
  message: string;
  jurisdiction: 'india' | 'international';
  session_id?: string;
}

export interface ChatResponse {
  message: {
    role: string;
    content: string;
    timestamp: string | null;
  };
  citations: any[];
  confidence: "low" | "medium" | "high";
  formulation_class: string | null;
  requires_escalation: boolean;
  session_id: string;
}

export interface Citation {
  source_id: string;
  section: string;
  article: string;
  version_hash: string;
  confidence: number;
  span_match?: string;
}

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `API error: ${response.statusText}`);
    }

    return response.json();
  }

  async getHealth(): Promise<{ status: string; services: any }> {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }
}

export const apiService = new ApiService();
