export type AssessmentStatus = "addressed" | "partial_evidence" | "not_found";

export interface DocumentEvidence {
  page: number;
  excerpt: string;
  matched_terms: string[];
}
export interface RelatedReference {
  source: string;
  standard: string;
  reference_text: string;
  retrieval_score: number;
}
export interface ESGFinding {
  id: string;
  pillar: "Environmental" | "Social" | "Governance";
  name: string;
  status: AssessmentStatus;
  evidence: DocumentEvidence[];
  related_references: RelatedReference[];
  assessment_note: string;
}
export interface DocumentAssessmentResponse {
  assessment_type: "document_disclosure_review";
  document: { filename: string; page_count: number };
  status: string;
  summary: { topic_count: number; counts: Record<AssessmentStatus, number> };
  pillars: Record<"Environmental" | "Social" | "Governance", ESGFinding[]>;
  methodology: string;
  limitations: string[];
}
