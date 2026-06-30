"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  profileSteps,
  type InitialProfileInput,
  type ProfileStep,
  type ProfileStepKey,
} from "@/data/profileOptions";
import { saveInitialProfile, setFirstRunStatus } from "@/data/user-writes";

type StepKey = ProfileStepKey;
type StepDef = Omit<ProfileStep, "key"> & { key: StepKey };

const STEPS: StepDef[] = profileSteps;

type Answers = {
  industry: string;
  jobType: string;
  position: string;
  recentInterests: string[];
  readingGenres: string[];
};

const EMPTY: Answers = {
  industry: "",
  jobType: "",
  position: "",
  recentInterests: [],
  readingGenres: [],
};

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Answers>(EMPTY);
  const [saving, setSaving] = useState(false);

  const cur = STEPS[step];
  const isLast = step === STEPS.length - 1;
  const value = answers[cur.key];

  const selected = (opt: string) =>
    cur.type === "single" ? value === opt : (value as string[]).includes(opt);

  const choose = (opt: string) => {
    setAnswers((a) => {
      if (cur.type === "single") return { ...a, [cur.key]: opt };
      const list = a[cur.key] as string[];
      const next = list.includes(opt) ? list.filter((o) => o !== opt) : [...list, opt];
      return { ...a, [cur.key]: next };
    });
  };

  const canProceed = (() => {
    if (!cur.required) return true;
    if (cur.type === "single") return value !== "";
    return (value as string[]).length >= (cur.minSelect ?? 1);
  })();

  const persist = async (skipped: boolean) => {
    setSaving(true);
    const profile: InitialProfileInput = {
      industry: answers.industry,
      jobType: answers.jobType,
      position: answers.position,
      recentInterests: answers.recentInterests,
      readingGenres: answers.readingGenres,
      serendipity: "バランス重視",
      skipped,
      createdAt: new Date().toISOString(),
    };
    try {
      await saveInitialProfile(profile);
    } catch (e) {
      // saveInitialProfile は内部で握りつぶす想定だが、二重の安全網。遷移は止めない。
      console.warn("初期プロフィール保存で例外（遷移は継続）", e);
    } finally {
      setSaving(false);
    }
    // 初回体験を開始：トップは「生成中」状態で開き、最初の本棚を仕立てる。
    setFirstRunStatus("generating");
    // 要望どおり登録後はトップ「あなたの書店」へ直接遷移する。
    router.push("/");
  };

  const onNext = () => {
    if (isLast) void persist(false);
    else setStep((s) => s + 1);
  };

  return (
    <div className="auth-frame">
      <div className="auth-card panel onb-card">
        <div className="onb-progress">
          {STEPS.map((s, i) => (
            <span key={s.key} className={`onb-dot ${i <= step ? "on" : ""}`} />
          ))}
        </div>
        <div className="onb-step-label">
          {step + 1} / {STEPS.length} ・ {cur.label}
        </div>
        <h1 className="onb-question">{cur.question}</h1>

        <div className="onb-options">
          {cur.options.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`chip onb-opt ${selected(opt) ? "on" : ""}`}
              onClick={() => choose(opt)}
            >
              {opt}
            </button>
          ))}
        </div>

        <div className="onb-actions">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0 || saving}
          >
            戻る
          </button>
          <button
            type="button"
            className="btn btn--gold"
            onClick={onNext}
            disabled={!canProceed || saving}
          >
            {saving ? "保存中…" : isLast ? "登録する" : "次へ"}
          </button>
        </div>

        <button type="button" className="onb-skip" onClick={() => void persist(true)} disabled={saving}>
          スキップする（あとで設定から調整できます）
        </button>
      </div>
    </div>
  );
}
