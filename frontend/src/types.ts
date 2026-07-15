export type LectureStatus =
  | "queued"
  | "normalizing"
  | "transcribing"
  | "generating"
  | "transcribed"
  | "completed"
  | "failed"
  | "cancelled"
  | "deleting";

export interface ProcessingMetrics {
  stage_seconds: Record<string, number>;
  total_seconds: number;
  peak_system_memory_mb: number;
}

export interface TranscriptSegment {
  id: string;
  start_ms: number;
  end_ms: number;
  text: string;
  confidence: number;
  uncertain: boolean;
}

export interface Transcript {
  language: string;
  duration_ms: number;
  segments: TranscriptSegment[];
}

export interface EvidenceItem {
  segment_ids: string[];
}

export interface StudyPack {
  title: string;
  overview: string;
  notes: Array<EvidenceItem & { title: string; body: string }>;
  concepts: Array<EvidenceItem & { name: string; definition: string }>;
  flashcards: Array<EvidenceItem & { front: string; back: string }>;
  quiz: Array<
    EvidenceItem & {
      question: string;
      options: string[];
      correct_answer: number;
      explanation: string;
    }
  >;
}

export interface LectureSummary {
  id: string;
  title: string;
  original_filename: string;
  status: LectureStatus;
  progress: number;
  message: string;
  metrics: ProcessingMetrics;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface LectureDetail extends LectureSummary {
  transcript: Transcript | null;
  study_pack: StudyPack | null;
}

export interface HealthResponse {
  ready: boolean;
  components: Record<
    string,
    { ready: boolean; detail: string; remediation: string | null }
  >;
}

export interface SegmentCorrection {
  segment_id: string;
  text: string;
}
