import type { ReactNode } from "react";
import Logo from "./Logo";
import styles from "./OnboardingFrame.module.css";

interface Props {
  children: ReactNode;
  step?: { current: number; total: number }; // ステッパー表示（初期登録）
  wide?: boolean;
}

/*
 * オンボーディング（ログイン/初期登録/データ連携）共通フレーム。
 * サイドバーなしの全画面センター型。上部に Publishr ブランド。
 */
export default function OnboardingFrame({ children, step, wide }: Props) {
  return (
    <div className={styles.screen}>
      <div className={styles.bg} />
      <header className={styles.brand}>
        <Logo size={44} />
        <span className={styles.logo}>Publishr</span>
        <span className={styles.tagline}>
          百万部のベストセラーより、あなたのための一冊。
        </span>
      </header>

      {step && (
        <div className={styles.stepper}>
          <div className={styles.stepBar}>
            <div
              className={styles.stepFill}
              style={{ width: `${(step.current / step.total) * 100}%` }}
            />
          </div>
          <span className={styles.stepText}>
            {step.current} / {step.total}
          </span>
        </div>
      )}

      <main className={`${styles.card} ${wide ? styles.wide : ""}`}>
        {children}
      </main>
    </div>
  );
}
