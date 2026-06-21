// Publishr 共有型（camelCase = JSON / API のシェイプ）。
// Python 側 packages/shared-schema/py/publishr_schema/models.py と一致させる。
//
// 正本:
//   - エージェント I/O: docs/design/agent-io-contract.md
//   - API 境界:        docs/design/api-contract.md
//   - Firestore ルール: docs/design/firestore-security-rules.md

export type BookStatus = "draft" | "reserved" | "writing" | "published";
export type Shelf = "arrivals" | "press" | "odd" | "library";
export type Granularity = "full" | "summary" | "excerpt";
export type AnnotationKind = "highlight" | "note" | "bookmark";
export type HighlightColor = "yellow" | "blue" | "pink";
export type Verdict = "採用" | "却下" | "保留";
export type ThemeKind = "honmei" | "serendipity";
export type Decision = "approve" | "revise";

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

// api-contract.md §2-a
export interface InitialProfile {
  industry: string;
  jobType: string;
  position: string;
  recentInterests: string[];
  readingGenres: string[];
  createdAt: string;
  skipped: boolean;
}

// tech-architecture.md §3: connectedSources（観測ソース接続・3ソース）
// Google Picker でフォルダ単位選択した folderIds[] をサーバ保持（G1-13）。
export interface DriveFolderLabel {
  folderId: string;
  label: string; // "業務" | "趣味"
}

export interface ConnectedSources {
  drive?: { enabled: boolean; folderIds: string[]; labels?: DriveFolderLabel[] };
  calendar?: { enabled: boolean; calendarIds?: string[] };
  tasks?: { enabled: boolean };
}

export interface User {
  id: string;
  name: string;
  initial: string;
  profile: UserProfile;
  // api-contract.md §2-a / §3-a
  initialProfile?: InitialProfile | null;
  favoriteAuthors?: Array<{ personaId: string; name: string; voiceStyle: string; format: string; savedAt: string }>;
  // tech-architecture.md §3: 観測ソース接続（STEP0 の入力・Picker=C4.1 が書込）
  connectedSources?: ConnectedSources | null;
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
  // agent-io-contract.md §5-3a
  voiceStyle?: string;       // narrative axis（文体軸）
  format?: string;           // writing format（形式軸）
  fromFavorite?: boolean;    // お気に入り著者由来か
  ephemeral?: boolean;       // 毎回生成（永続しない）
}

export interface Plan {
  id: string;
  reason: string;
  coreMessage: string;
  readerSituation: string;
  differentiator: string;
  agendaOutline: string[];
  recommendedAuthorTypes: string[];
  // agent-io-contract.md §4-2b (PlanProposal)
  proposalId?: string;
  themeKind?: ThemeKind | string;
  round?: number;
  tentativeTitle?: string;
  whyNowForYou?: string;
  diffFromMarket?: string;   // 正本名（differentiator は後方互換で残す）
  keyInsights?: string[];
}

export interface Observation {
  noteCount: number;
  topLabels: string[];
  signals: string[];
}

// agent-io-contract.md §3: ReaderProfile 3 層構造
export interface ReaderProfileBase {
  industry: string;
  jobType: string;
  position: string;
  orgScale: string;
  readingGenres: string[];
}

export interface ReaderProfileCurrentWork {
  currentSituation: string;
  activeWorkThemes: string[];
  challenges: string[];
  upcomingKeyEvents: Array<{ title: string; date: string }>;
  evidence: Array<{ claim: string; source: string }>;
}

export interface ReaderProfileReadingBehavior {
  recentReads: Array<{ title: string; theme: string }>;
  highlightsSummary: string;
  dropSignals: Array<{ title: string; reason: string }>;
  feedbackSummary: string;
  serendipityTolerance: string;
  stylePreference: string;
}

export interface ReaderProfile {
  // 既存フラット構造（後方互換）
  role: string;
  situation: string;
  interests: string[];
  signals: string[];
  serendipityTolerance: string;
  // agent-io-contract.md §3: 3 層構造（エージェント実装側で使う）
  base?: ReaderProfileBase | null;
  currentWork?: ReaderProfileCurrentWork | null;
  readingBehavior?: ReaderProfileReadingBehavior | null;
}

export interface PlanningCandidate {
  key: string;
  persona: string;
  candidate: string;
  planId: string | null;
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
  readingReaction?: string | null;
  lastReadAt?: string | null; // 最後に読んだ時刻(ISO8601)。「最近読んだ本」の並び順に使う
  impression?: string | null; // 読了時の自由記述感想（untrusted。学習ループ利用時は要正規化）
}

export interface ReadingAnnotation {
  id: string;
  kind: AnnotationKind;
  paragraphIndex: number;
  text: string;
  note?: string | null;
  // ハイライト用（省略時は段落全体、後方互換）
  color?: HighlightColor;
  startOffset?: number;
  endOffset?: number;
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
  annotations: ReadingAnnotation[];
  feedback: Feedback;
  createdAt?: string;
  // agent-io-contract.md §5-2a (BookDraft) 追加フィールド
  ownerUid?: string;          // Firestore セキュリティルールの根幹
  kind?: ThemeKind | string;  // "honmei" | "serendipity"
  deliveryReason?: string;    // 書店 UI「入荷理由」表示
  problemToSolve?: string;    // 本詳細: 解決する課題
  coreMessage?: string;       // 本詳細: 核心メッセージ
  editRound?: number;         // 編集ループ回数
  bodyUrl?: string | null;    // GCS 本文 URL（Mode B 完了後）
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
  observation: Observation;
  readerProfile: ReaderProfile;
  candidates: PlanningCandidate[];
  approvedPlanIds: string[];
  rejectLog: RejectLogEntry[];
}

// POST /books/{id}/feedback のリクエスト
export interface FeedbackInput {
  readPercent?: number;
  dropped?: boolean;
  rating?: number | null;
  wantsSequel?: boolean;
  readingReaction?: string | null;
  lastReadAt?: string; // 通常はクライアント/サーバが読了率更新時に自動付与
  impression?: string; // 自由記述感想（サーバで制御文字除去＋長さ制限して保存）
}

export interface ReadingStateInput {
  granularity?: Granularity;
  annotations?: ReadingAnnotation[];
}

// ===========================================================================
// 以下: agent-io-contract.md 由来の新規型（エージェント I/O 専用）
// ===========================================================================

// ---------------------------------------------------------------------------
// STEP0: ObservationBundle（§2）
// ---------------------------------------------------------------------------
export interface DriveFile {
  fileId: string;
  name: string;
  mimeType: string;
  folderLabel: string;
  textExcerpt: string;
  modifiedTime: string;
}

export interface CalendarEvent {
  title: string;
  start: string;
  end: string;
  attendeesCount: number;
  recurring: boolean;
}

export interface TaskItem {
  title: string;
  due?: string | null;
  status: string;
  notes: string;
}

export interface ObservationBundle {
  userId: string;
  collectedAt: string;
  drive: { files: DriveFile[] };
  calendar: { events: CalendarEvent[] };
  tasks: { items: TaskItem[] };
  readingFb: {
    highlights: Array<{ bookId: string; text: string; createdAt: string }>;
    logs: Array<{ bookId: string; readPercent: number; dropped: boolean; dwellSec: number }>;
    simpleFb: Array<{ bookId: string; rating: number; wantsSequel: boolean }>;
  };
}

// ---------------------------------------------------------------------------
// STEP2a: LeaderVerdict（§4-2a）企画リーダーの採点
// ---------------------------------------------------------------------------
export interface LeaderScoreBreakdown {
  relevance: number;       // 0-25
  differentiation: number; // 0-25
  researchUse: number;     // 0-25
  titleHook: number;       // 0-25
}

export interface LeaderVerdict {
  round: number;
  score: number;
  scoreBreakdown: LeaderScoreBreakdown;
  belowFloor: boolean;
  decision: Decision;
  rejectionFeedback: string | null;
  approvedPlan: Plan | null;
}

// ---------------------------------------------------------------------------
// STEP2c: Research サブエージェント出力（§4-2c）
// ---------------------------------------------------------------------------
export interface SubReaderContext {
  painPoints: Array<{ pain: string; evidence: string }>;
  decisions: Array<{ context: string; evidence: string }>;
  evidence: Array<{ claim: string; source: string }>;
}

export interface SubMarket {
  themeKind: string;
  queries: string[];
  findings: Array<{ title: string; point: string; source: string }>;
  marketGap: string;
}

export interface SubThemeInsight {
  keyPoints: Array<{ insight: string; framework: string; source: string }>;
}

// ---------------------------------------------------------------------------
// STEP4: EditorVerdict（§5-2b）編集長の採点
// ---------------------------------------------------------------------------
export interface EditorScoreBreakdown {
  rawInsight: number;      // 0-34
  personaForward: number;  // 0-33
  catchiness: number;      // 0-33
}

export interface EditorVerdict {
  bookId: string;
  round: number;
  score: number;
  scoreBreakdown: EditorScoreBreakdown;
  decision: Decision;
  editorFeedback: string | null;
}
