export type LectureStatus =
  | "queued"
  | "normalizing"
  | "transcribing"
  | "generating"
  | "completed"
  | "failed"
  | "deleting";

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
  original_filename: string;
  status: LectureStatus;
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
  components: Record<string, { ready: boolean; detail: string }>;
}
