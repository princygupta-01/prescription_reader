import { UploadResponse, PollResponse, Stats } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadPrescription(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

export async function pollResult(taskId: string): Promise<PollResponse> {
  const response = await fetch(`${API_BASE}/api/result/${taskId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to get result' }));
    throw new Error(error.detail || 'Failed to get result');
  }

  return response.json();
}

export async function exportPdf(prescriptionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/export/${prescriptionId}/pdf`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'PDF export failed' }));
    throw new Error(error.detail || 'PDF export failed');
  }

  // Create blob and trigger download
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `prescription_${prescriptionId}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function getStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE}/api/stats`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to get stats' }));
    throw new Error(error.detail || 'Failed to get stats');
  }

  return response.json();
}

export async function healthCheck(): Promise<{ status: string; models_loaded: boolean; groq_connected: boolean }> {
  const response = await fetch(`${API_BASE}/health`);

  if (!response.ok) {
    throw new Error('Health check failed');
  }

  return response.json();
}