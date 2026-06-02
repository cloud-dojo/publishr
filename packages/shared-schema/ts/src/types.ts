// Publishr 共有型（camelCase = JSON / API のシェイプ）。
// Python 側 packages/shared-schema/py/publishr_schema/models.py と一致させる。

export type BookStatus = "draft" | "reserved" | "writing" | "published";
export type Shelf = "arrivals" | "press" | "odd" | "library";
export type Granularity = "full" | "summary" | "excerpt";
export type Verdict = "採用" | "却下" | "保留";

export interface ChecklistItem {
  text: string;
  checked: boolean;
}

export interface KeepNote {
  id: string;
  userId: string;
  title: string;
  text: string;
  labels: string[];
  checklist: ChecklistItem[];
  pinned: boolean;
  updatedAt: string;
}

export interface UserProfile {
  role: string;
  workTheme: string;
  estimatedInterests: string[];
  serendipityTolerance: string;
}

export interface User {
  id: string;
  name: string;
  initial: string;
  profile: UserProfile;
}

export interface PastBook {
  bookId: string;
  title: string;
  userRating: number;
}

export interface PersonaDetail {
  career: string;
  styleNote: string;
  thought: string;
  signature: string[];
  themes: string[];
}

export interface Persona {
  id: string;
  name: string;
  nameReading: string;
  monogram: string;
  style: string;
  title: string;
  persona: PersonaDetail;
  expertise: string[];
  pastBooks: PastBook[];
}

export interface Plan {
  id: string;
  reason: string;
  coreMessage: string;
  readerSituation: string;
  differentiator: string;
  agendaOutline: string[];
  recommendedAuthorTypes: string[];
}

export interface AgendaItem {
  no: string;
  title: string;
  desc: string;
  locked: boolean;
  note?: string | null;
}

export interface Feedback {
  readPercent: number;
  dropped: boolean;
  rating: number | null;
  wantsSequel: boolean;
}

export interface Book {
  id: string;
  planId: string;
  status: BookStatus;
  authorPersonaId: string;
  title: string;
  subtitle: string;
  coverVariant: string;
  coverUrl: string | null;
  shelf: Shelf;
  estimatedChapters: number;
  estimatedMinutes: number;
  granularity: Granularity;
  prefaceSample: string;
  agenda: AgendaItem[];
  body: string | null;
  feedback: Feedback;
}

// 企画会議の「却下→再提出」ログ（基準1の証拠）
export interface RejectLogEntry {
  round: number;
  candidate: string;
  persona: string;
  verdict: Verdict;
  reason: string;
}

// POST /pipeline/run の戻り
export interface PipelineResult {
  plans: Plan[];
  books: Book[];
  rejectLog: RejectLogEntry[];
}

// POST /books/{id}/feedback のリクエスト
export interface FeedbackInput {
  readPercent?: number;
  dropped?: boolean;
  rating?: number | null;
  wantsSequel?: boolean;
}
