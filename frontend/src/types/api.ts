/**
 * Data Contract Types - TypeScript
 * Matches backend/models/schemas.py
 */

// ============================================================================
// REQUEST TYPES
// ============================================================================

export interface CompareRequest {
  v1_text: string;
  v2_text: string;
}

// ============================================================================
// RESPONSE TYPES
// ============================================================================

export interface SentencePair {
  pair_id: string;
  v1_sentence: string | null;
  v2_sentence: string | null;
  v1_index: number | null;
  v2_index: number | null;
  similarity_score: number;
  status: "matched" | "added" | "deleted";
  severity: "green" | "yellow" | "red" | "added" | "deleted";
  explanation: string | null;
}

export interface DocumentSummary {
  overall_score: number;
  total_pairs: number;
  green_count: number;
  yellow_count: number;
  red_count: number;
  added_count: number;
  deleted_count: number;
}

export interface CompareResponse {
  comparison_id: string;
  pairs: SentencePair[];
  summary: DocumentSummary;
}

export interface ExplanationResponse {
  comparison_id: string;
  status: "pending" | "partial" | "complete";
  explanations: Record<string, string | null>;
}

// ============================================================================
// SEVERITY COLORS
// ============================================================================

export const SEVERITY_COLORS = {
  green: "#22c55e",
  yellow: "#eab308",
  red: "#ef4444",
  added: "#3b82f6",
  deleted: "#6b7280"
} as const;

export const SEVERITY_BACKGROUNDS = {
  green: "rgba(34, 197, 94, 0.2)",
  yellow: "rgba(234, 179, 8, 0.2)",
  red: "rgba(239, 68, 68, 0.2)",
  added: "rgba(59, 130, 246, 0.2)",
  deleted: "rgba(107, 114, 128, 0.2)"
} as const;
