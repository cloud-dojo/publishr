// zod スキーマ: データ境界（プロバイダ）で実行時バリデーションに使う。
// types.ts と対応。
//
// 正本: docs/design/agent-io-contract.md / api-contract.md

import { z } from "zod";

export const bookStatusSchema = z.enum(["draft", "reserved", "writing", "published"]);
export const shelfSchema = z.enum(["arrivals", "press", "odd", "library"]);
export const granularitySchema = z.enum(["full", "summary", "excerpt"]);
export const annotationKindSchema = z.enum(["highlight", "note", "bookmark"]);
export const verdictSchema = z.enum(["採用", "却下", "保留"]);
export const themeKindSchema = z.enum(["honmei", "serendipity"]);
export const decisionSchema = z.enum(["approve", "revise"]);

export const checklistItemSchema = z.object({
  text: z.string(),
  checked: z.boolean(),
});

export const keepNoteSchema = z.object({
  id: z.string(),
  userId: z.string(),
  title: z.string(),
  text: z.string(),
  labels: z.array(z.string()),
  checklist: z.array(checklistItemSchema),
  pinned: z.boolean(),
  updatedAt: z.string(),
});

export const userProfileSchema = z.object({
  role: z.string(),
  workTheme: z.string(),
  estimatedInterests: z.array(z.string()),
  serendipityTolerance: z.string(),
});

export const initialProfileSchema = z.object({
  industry: z.string(),
  jobType: z.string(),
  position: z.string(),
  recentInterests: z.array(z.string()).default([]),
  readingGenres: z.array(z.string()).default([]),
  createdAt: z.string().default(""),
  skipped: z.boolean().default(false),
});

export const favoriteAuthorEntrySchema = z.object({
  personaId: z.string(),
  name: z.string(),
  voiceStyle: z.string(),
  format: z.string(),
  savedAt: z.string(),
});

export const userSchema = z.object({
  id: z.string(),
  name: z.string(),
  initial: z.string(),
  profile: userProfileSchema,
  initialProfile: initialProfileSchema.nullable().optional(),
  favoriteAuthors: z.array(favoriteAuthorEntrySchema).default([]),
});

export const pastBookSchema = z.object({
  bookId: z.string(),
  title: z.string(),
  userRating: z.number(),
});

export const personaSchema = z.object({
  id: z.string(),
  name: z.string(),
  nameReading: z.string(),
  monogram: z.string(),
  style: z.string(),
  title: z.string(),
  persona: z.object({
    career: z.string(),
    styleNote: z.string(),
    thought: z.string(),
    signature: z.array(z.string()),
    themes: z.array(z.string()),
  }),
  expertise: z.array(z.string()),
  pastBooks: z.array(pastBookSchema),
  // agent-io-contract.md §5-3a
  voiceStyle: z.string().default(""),
  format: z.string().default(""),
  fromFavorite: z.boolean().default(false),
  ephemeral: z.boolean().default(true),
});

export const planSchema = z.object({
  id: z.string(),
  reason: z.string(),
  coreMessage: z.string(),
  readerSituation: z.string(),
  differentiator: z.string(),
  agendaOutline: z.array(z.string()),
  recommendedAuthorTypes: z.array(z.string()),
  // agent-io-contract.md §4-2b
  proposalId: z.string().default(""),
  themeKind: z.string().default(""),
  round: z.number().default(0),
  tentativeTitle: z.string().default(""),
  whyNowForYou: z.string().default(""),
  diffFromMarket: z.string().default(""),
  keyInsights: z.array(z.string()).default([]),
});

export const observationSchema = z.object({
  noteCount: z.number(),
  topLabels: z.array(z.string()),
  signals: z.array(z.string()),
});

export const readerProfileBaseSchema = z.object({
  industry: z.string().default(""),
  jobType: z.string().default(""),
  position: z.string().default(""),
  orgScale: z.string().default(""),
  readingGenres: z.array(z.string()).default([]),
});

export const readerProfileCurrentWorkSchema = z.object({
  currentSituation: z.string().default(""),
  activeWorkThemes: z.array(z.string()).default([]),
  challenges: z.array(z.string()).default([]),
  upcomingKeyEvents: z.array(z.object({ title: z.string(), date: z.string() })).default([]),
  evidence: z.array(z.object({ claim: z.string(), source: z.string() })).default([]),
});

export const readerProfileReadingBehaviorSchema = z.object({
  recentReads: z.array(z.object({ title: z.string(), theme: z.string() })).default([]),
  highlightsSummary: z.string().default(""),
  dropSignals: z.array(z.object({ title: z.string(), reason: z.string() })).default([]),
  feedbackSummary: z.string().default(""),
  serendipityTolerance: z.string().default(""),
  stylePreference: z.string().default(""),
});

export const readerProfileSchema = z.object({
  role: z.string(),
  situation: z.string(),
  interests: z.array(z.string()),
  signals: z.array(z.string()),
  serendipityTolerance: z.string(),
  // agent-io-contract.md §3: 3 層構造
  base: readerProfileBaseSchema.nullable().optional(),
  currentWork: readerProfileCurrentWorkSchema.nullable().optional(),
  readingBehavior: readerProfileReadingBehaviorSchema.nullable().optional(),
});

export const planningCandidateSchema = z.object({
  key: z.string(),
  persona: z.string(),
  candidate: z.string(),
  planId: z.string().nullable(),
});

export const agendaItemSchema = z.object({
  no: z.string(),
  title: z.string(),
  desc: z.string(),
  locked: z.boolean(),
  note: z.string().nullish(),
});

export const feedbackSchema = z.object({
  readPercent: z.number(),
  dropped: z.boolean(),
  rating: z.number().nullable(),
  wantsSequel: z.boolean(),
  readingReaction: z.string().nullish(),
  lastReadAt: z.string().nullish(), // 最後に読んだ時刻(ISO8601)
  impression: z.string().nullish(), // 読了時の自由記述感想
});

export const readingAnnotationSchema = z.object({
  id: z.string(),
  kind: annotationKindSchema,
  paragraphIndex: z.number(),
  text: z.string(),
  note: z.string().nullish(),
});

export const bookSchema = z.object({
  id: z.string(),
  planId: z.string(),
  status: bookStatusSchema,
  authorPersonaId: z.string(),
  title: z.string(),
  subtitle: z.string(),
  coverVariant: z.string(),
  coverUrl: z.string().nullable(),
  shelf: shelfSchema,
  estimatedChapters: z.number(),
  estimatedMinutes: z.number(),
  granularity: granularitySchema,
  prefaceSample: z.string(),
  agenda: z.array(agendaItemSchema),
  body: z.string().nullable(),
  annotations: z.array(readingAnnotationSchema).default([]),
  feedback: feedbackSchema,
  createdAt: z.string().optional(),
  // agent-io-contract.md §5-2a
  ownerUid: z.string().default(""),
  kind: z.string().default(""),
  deliveryReason: z.string().default(""),
  problemToSolve: z.string().default(""),
  coreMessage: z.string().default(""),
  editRound: z.number().default(0),
  bodyUrl: z.string().nullable().optional(),
});

export const rejectLogEntrySchema = z.object({
  round: z.number(),
  candidate: z.string(),
  persona: z.string(),
  verdict: verdictSchema,
  reason: z.string(),
});

export const pipelineResultSchema = z.object({
  plans: z.array(planSchema),
  books: z.array(bookSchema),
  observation: observationSchema,
  readerProfile: readerProfileSchema,
  candidates: z.array(planningCandidateSchema),
  approvedPlanIds: z.array(z.string()),
  rejectLog: z.array(rejectLogEntrySchema),
});

// ===========================================================================
// 以下: agent-io-contract.md 由来の新規スキーマ（エージェント I/O 専用）
// ===========================================================================

// STEP0: ObservationBundle（§2）
export const driveFileSchema = z.object({
  fileId: z.string(),
  name: z.string(),
  mimeType: z.string(),
  folderLabel: z.string().default(""),
  textExcerpt: z.string().default(""),
  modifiedTime: z.string(),
});

export const calendarEventSchema = z.object({
  title: z.string(),
  start: z.string(),
  end: z.string(),
  attendeesCount: z.number().default(0),
  recurring: z.boolean().default(false),
});

export const taskItemSchema = z.object({
  title: z.string(),
  due: z.string().nullable().optional(),
  status: z.string().default("needsAction"),
  notes: z.string().default(""),
});

export const observationBundleSchema = z.object({
  userId: z.string(),
  collectedAt: z.string(),
  drive: z.object({ files: z.array(driveFileSchema) }),
  calendar: z.object({ events: z.array(calendarEventSchema) }),
  tasks: z.object({ items: z.array(taskItemSchema) }),
  readingFb: z.object({
    highlights: z.array(z.object({ bookId: z.string(), text: z.string(), createdAt: z.string() })),
    logs: z.array(z.object({ bookId: z.string(), readPercent: z.number(), dropped: z.boolean(), dwellSec: z.number() })),
    simpleFb: z.array(z.object({ bookId: z.string(), rating: z.number(), wantsSequel: z.boolean() })),
  }),
});

// STEP2a: LeaderVerdict（§4-2a）
export const leaderScoreBreakdownSchema = z.object({
  relevance: z.number(),
  differentiation: z.number(),
  researchUse: z.number(),
  titleHook: z.number(),
});

export const leaderVerdictSchema = z.object({
  round: z.number(),
  score: z.number(),
  scoreBreakdown: leaderScoreBreakdownSchema,
  belowFloor: z.boolean(),
  decision: decisionSchema,
  rejectionFeedback: z.string().nullable(),
  approvedPlan: z.any().nullable(),
});

// STEP2c: Research サブ出力（§4-2c）
export const subReaderContextSchema = z.object({
  painPoints: z.array(z.record(z.string(), z.unknown())),
  decisions: z.array(z.record(z.string(), z.unknown())),
  evidence: z.array(z.record(z.string(), z.unknown())),
});

export const subMarketSchema = z.object({
  themeKind: z.string(),
  queries: z.array(z.string()),
  findings: z.array(z.record(z.string(), z.unknown())),
  marketGap: z.string(),
});

export const subThemeInsightSchema = z.object({
  keyPoints: z.array(z.record(z.string(), z.unknown())),
});

// STEP4: EditorVerdict（§5-2b）
export const editorScoreBreakdownSchema = z.object({
  rawInsight: z.number(),
  personaForward: z.number(),
  catchiness: z.number(),
});

export const editorVerdictSchema = z.object({
  bookId: z.string(),
  round: z.number(),
  score: z.number(),
  scoreBreakdown: editorScoreBreakdownSchema,
  decision: decisionSchema,
  editorFeedback: z.string().nullable(),
});
