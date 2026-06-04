import { useNavigate } from "react-router-dom";
import OnboardingFrame from "../components/OnboardingFrame";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const navigate = useNavigate();

  return (
    <OnboardingFrame>
      <div className={styles.body}>
        <p className={styles.lead}>
          あなたの仕事と関心を観測し、
          <br />
          毎週、あなただけの一冊を出版します。
        </p>

        <button className={styles.googleBtn} onClick={() => navigate("/onboarding")}>
          <span className={styles.gIcon} aria-hidden>
            G
          </span>
          Googleでログイン
        </button>

        <p className={styles.note}>
          ログインすると、次に Google Drive・Calendar・Tasks
          の観測について同意をお願いします。
        </p>

        <div className={styles.demoHint}>
          <span className={styles.demoLabel}>DEMO</span>
          このボタンは初期登録画面に進みます（Firebase Auth は未接続）。
        </div>
      </div>
    </OnboardingFrame>
  );
}
