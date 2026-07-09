import { useState } from "react";
import { useNavigate } from "react-router-dom";
import OnboardingFrame from "../components/OnboardingFrame";
import { profileSteps } from "../data/profileOptions";
import styles from "./OnboardingPage.module.css";

type Selections = Record<string, string[]>;

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [stepIdx, setStepIdx] = useState(0);
  const [selections, setSelections] = useState<Selections>({});

  const step = profileSteps[stepIdx];
  const selected = selections[step.key] ?? [];
  const isLast = stepIdx === profileSteps.length - 1;
  const canProceed = !step.required || selected.length > 0;

  const toggle = (opt: string) => {
    setSelections((prev) => {
      const cur = prev[step.key] ?? [];
      if (step.multi) {
        return {
          ...prev,
          [step.key]: cur.includes(opt)
            ? cur.filter((o) => o !== opt)
            : [...cur, opt],
        };
      }
      return { ...prev, [step.key]: [opt] };
    });
    // 単一選択は選んだら自動で次へ進める（最後は除く）
    if (!step.multi && !isLast) {
      setTimeout(() => setStepIdx((i) => Math.min(i + 1, profileSteps.length - 1)), 220);
    }
  };

  const next = () => {
    if (isLast) {
      // 実装では users/{uid}.initialProfile へ直書き → データ連携へ
      navigate("/connect");
    } else {
      setStepIdx((i) => i + 1);
    }
  };

  return (
    <OnboardingFrame step={{ current: stepIdx + 1, total: profileSteps.length }} wide>
      <div className={styles.head}>
        <span className="eyebrow">Tell us about you</span>
        <h1 className={styles.title}>{step.title}</h1>
        <p className={styles.caption}>{step.caption}</p>
      </div>

      <div className={styles.options}>
        {step.options.map((opt) => (
          <button
            key={opt}
            className={`${styles.opt} ${selected.includes(opt) ? styles.on : ""}`}
            onClick={() => toggle(opt)}
          >
            {opt}
          </button>
        ))}
      </div>

      <div className={styles.footer}>
        <button
          className={styles.back}
          onClick={() => setStepIdx((i) => Math.max(0, i - 1))}
          disabled={stepIdx === 0}
        >
          ← 戻る
        </button>

        <button className={styles.skip} onClick={() => navigate("/connect")}>
          スキップする
        </button>

        <button className={styles.next} onClick={next} disabled={!canProceed}>
          {isLast ? "登録する →" : "次へ →"}
        </button>
      </div>
    </OnboardingFrame>
  );
}
