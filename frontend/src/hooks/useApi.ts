import { API_BASE } from '../lib/constants';
import type { AskResponse, RunSummary, HealthInfo } from '../types';
import type { AppMode } from '../lib/constants';

export async function apiAsk(
  question: string,
  mode: AppMode,
  topK: number = 5,
): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, mode, top_k: topK }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `Server error: ${res.status}`);
  }

  return res.json();
}

export async function apiGetRun(runId: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error('Failed to load run details');
  return res.json();
}

export async function apiGetRuns(limit: number = 20): Promise<RunSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/runs?limit=${limit}`);
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function apiGetHealth(): Promise<HealthInfo | null> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function apiGetEvalSummary() {
  const res = await fetch(`${API_BASE}/eval/summary`);
  if (!res.ok) throw new Error('Failed to load evaluation summary');
  return res.json();
}

export async function apiGetEvalRuns(split?: string) {
  const url = split ? `${API_BASE}/eval/runs?split=${split}` : `${API_BASE}/eval/runs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to load evaluation runs');
  return res.json();
}

export async function apiGetEvalErrors() {
  const res = await fetch(`${API_BASE}/eval/errors`);
  if (!res.ok) throw new Error('Failed to load evaluation error analysis');
  return res.json();
}

export async function apiGetPerQueryMetrics() {
  const res = await fetch(`${API_BASE}/eval/per-query`);
  if (!res.ok) throw new Error('Failed to load per-query evaluation metrics');
  return res.json();
}
