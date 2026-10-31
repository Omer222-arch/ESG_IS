
import type { DocumentAssessmentResponse } from "../types/documentAssessment";
import { getCsrfToken } from "./client";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export async function assessESGDocument(
  file: File,
): Promise<DocumentAssessmentResponse> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(
    `${API_BASE}/api/v1/esg/document-assessment`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
      body: form,
    },
  );

  if (!response.ok) {
    let message = response.statusText || "Document assessment failed";
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail || message;
    } catch {
      // Response was not JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<DocumentAssessmentResponse>;
}
