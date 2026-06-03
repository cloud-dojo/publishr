// zod スキーマ: データ境界（プロバイダ）で実行時バリデーションに使う。
// types.ts と対応。

import { z } from "zod";

export const bookStatusSchema = z.enum(["draft", "reserved", "writing", "published"]);
export const shelfSchema = z.enum(["arrivals", "press", "odd", "library"]);
export const granularitySchema = z.enum(["full", "summary", "excerpt"]);
export const annotationKindSchema = z.enum(["highlight", "note", "bookmark"]);
export const verdictSchema = z.enum(["採用", "却下", "保留"]);

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

export const userSchema = z.object({
  id: z.string(),
  name: z.string(),
  initial: z.string(),
  profile: userProfileSchema,
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
});

export const planSchema = z.object({
  id: z.string(),
  reason: z.string(),
  coreMessage: z.string(),
  readerSituation: z.string(),
  differentiator: z.string(),
  agendaOutline: z.array(z.string()),
  recommendedAuthorTypes: z.array(z.string()),
});

export const observationSchema = z.object({
  noteCount: z.number(),
  topLabels: z.array(z.string()),
  signals: z.array(z.string()),
});

export const readerProfileSchema = z.object({
  role: z.string(),
  situation: z.string(),
  interests: z.array(z.string()),
  signals: z.array(z.string()),
  serendipityTolerance: z.string(),
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
