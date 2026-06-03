"use client";

import { useEffect, useReducer } from "react";

import type {
  Book,
  Observation,
  Persona,
  Plan,
  PlanningCandidate,
  ReaderProfile,
  RejectLogEntry,
  User,
} from "@publishr/shared-schema";

import { getProvider } from "./index";
import type { BaseProvider } from "./provider";

/** プロバイダを購読し、変更時に再レンダリングする基礎フック。 */
export function useProvider(): BaseProvider {
  const provider = getProvider();
  const [, force] = useReducer((c: number) => c + 1, 0);
  useEffect(() => {
    const unsub = provider.subscribe(force);
    void provider.ensureLoaded();
    return unsub;
  }, [provider]);
  return provider;
}

export function useBooks(): { books: Book[]; ready: boolean } {
  const provider = useProvider();
  return { books: provider.listBooks(), ready: provider.ready };
}

export function useBook(id: string): { book: Book | undefined; ready: boolean } {
  const provider = useProvider();
  return { book: provider.getBook(id), ready: provider.ready };
}

export function usePlan(id: string | undefined): Plan | undefined {
  const provider = useProvider();
  return id ? provider.getPlan(id) : undefined;
}

export function usePersona(id: string | undefined): Persona | undefined {
  const provider = useProvider();
  return id ? provider.getPersona(id) : undefined;
}

export function useUser(id: string): User | undefined {
  const provider = useProvider();
  return provider.getUser(id);
}

export function useDebate(): RejectLogEntry[] {
  const provider = useProvider();
  return provider.getDebate();
}

export function usePlanningCandidates(): {
  candidates: PlanningCandidate[];
  approvedPlanIds: string[];
} {
  const provider = useProvider();
  return {
    candidates: provider.getCandidates(),
    approvedPlanIds: provider.getApprovedPlanIds(),
  };
}

export function useReaderAnalysis(): {
  observation: Observation | null;
  readerProfile: ReaderProfile | null;
} {
  const provider = useProvider();
  return {
    observation: provider.getObservation(),
    readerProfile: provider.getReaderProfile(),
  };
}

export function useActions() {
  const provider = getProvider();
  return {
    reserve: (id: string) => provider.reserve(id),
    sendFeedback: provider.sendFeedback.bind(provider),
    updateReadingState: provider.updateReadingState.bind(provider),
    runPipeline: (userId: string) => provider.runPipeline(userId),
  };
}
