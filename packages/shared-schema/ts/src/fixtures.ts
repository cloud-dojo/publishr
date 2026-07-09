// 共有JSONフィクスチャの型付き再エクスポート（Python側と同一データを参照）。
import booksJson from "../../fixtures/books.json";
import keepNotesJson from "../../fixtures/keep_notes.json";
import personasJson from "../../fixtures/personas.json";
import plansJson from "../../fixtures/plans.json";
import usersJson from "../../fixtures/users.json";
import type { Book, KeepNote, Persona, Plan, User } from "./types";

export const users = usersJson as unknown as User[];
export const personas = personasJson as unknown as Persona[];
export const plans = plansJson as unknown as Plan[];
export const books = booksJson as unknown as Book[];
export const keepNotes = keepNotesJson as unknown as KeepNote[];
