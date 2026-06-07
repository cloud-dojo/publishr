"use client";

import { useEffect, useState } from "react";
import type { User } from "@publishr/shared-schema";
import { useRouter } from "next/navigation";

import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID } from "@/data/config";
import { useProvider } from "@/data/hooks";
import { signOutUser, watchAuth } from "@/lib/firebase";
import { MOCK_HIGHLIGHTS } from "@/data/mock-highlights";
import {
  optionsFor,
  serendipityOptions,
  type InitialProfileInput,
} from "@/data/profileOptions";
import { getInitialProfile, saveInitialProfile } from "@/data/user-writes";

const CONNECTED = [
  { name: "Google Drive", icon: "📁" },
  { name: "Google Calendar", icon: "📅" },
  { name: "Google Tasks", icon: "✓" },
];

const INDUSTRY = optionsFor("industry");
const JOBTYPE = optionsFor("jobType");
const POSITION = optionsFor("position");
const INTERESTS = optionsFor("recentInterests");

function Mini({ n, label }: { n: number; label: string }) {
  return (
    <div className="acct-mini">
      <span className="am-num">{n}</span>
      <span className="am-label">{label}</span>
    </div>
  );
}

type EditForm = {
  industry: string;
  jobType: string;
  position: string;
  serendipity: string;
  recentInterests: string[];
};

function buildInitial(user: User): EditForm {
  const saved = getInitialProfile();
  if (saved) {
    return {
      industry: saved.industry ?? "",
      jobType: saved.jobType ?? "",
      position: saved.position ?? "",
      serendipity: saved.serendipity ?? "バランス重視",
      recentInterests: saved.recentInterests ?? [],
    };
  }
  // 保存値が無ければ mock ユーザーから当たりを付ける。
  const prefillInterests = (user.profile?.estimatedInterests ?? []).filter((i) =>
    INTERESTS.includes(i)
  );
  return {
    industry: "",
    jobType: "",
    position: "",
    serendipity: "バランス重視",
    recentInterests: prefillInterests,
  };
}

/** 初期プロフィール編集フォーム。user 確定後（クライアント）にのみマウントされる。 */
function ProfileEditor({ user }: { user: User }) {
  const [form, setForm] = useState<EditForm>(() => buildInitial(user));
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const set = <K extends keyof EditForm>(key: K, value: EditForm[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setSavedMsg(null);
  };

  const toggleInterest = (opt: string) => {
    setForm((f) => ({
      ...f,
      recentInterests: f.recentInterests.includes(opt)
        ? f.recentInterests.filter((x) => x !== opt)
        : [...f.recentInterests, opt],
    }));
    setSavedMsg(null);
  };

  const onSave = async () => {
    setSaving(true);
    const prev = getInitialProfile();
    const profile: InitialProfileInput = {
      industry: form.industry,
      jobType: form.jobType,
      position: form.position,
      recentInterests: form.recentInterests,
      readingGenres: prev?.readingGenres ?? [],
      serendipity: form.serendipity,
      skipped: false,
      createdAt: prev?.createdAt ?? new Date().toISOString(),
    };
    try {
      await saveInitialProfile(profile);
      setSavedMsg("プロフィールを更新しました。来週の企画から反映されます。");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {/* 登録情報（業界・職種・役職） */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Registered profile</div>
            <div className="section-title">登録情報</div>
            <div className="section-sub">いつでも選び直して、更新できます。</div>
          </div>
        </div>
        <div className="acct-fields">
          <label className="acct-field">
            <span>業界</span>
            <select
              className="acct-select"
              value={form.industry}
              onChange={(e) => set("industry", e.target.value)}
            >
              <option value="">未設定</option>
              {INDUSTRY.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
          <label className="acct-field">
            <span>職種</span>
            <select
              className="acct-select"
              value={form.jobType}
              onChange={(e) => set("jobType", e.target.value)}
            >
              <option value="">未設定</option>
              {JOBTYPE.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
          <label className="acct-field">
            <span>役職</span>
            <select
              className="acct-select"
              value={form.position}
              onChange={(e) => set("position", e.target.value)}
            >
              <option value="">未設定</option>
              {POSITION.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {/* 新しい出会いの幅（旧セレンディピティ許容度） */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Serendipity</div>
            <div className="section-title">新しい出会いの幅</div>
            <div className="section-sub">
              いつもの関心から、どれくらい離れた本も混ぜてほしいですか。
            </div>
          </div>
        </div>
        <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
          {serendipityOptions.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`chip ${form.serendipity === opt ? "on" : ""}`}
              onClick={() => set("serendipity", opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </section>

      {/* いまの関心（タグをワンクリックでトグル） */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Your interests</div>
            <div className="section-title">いまの関心</div>
            <div className="section-sub">
              気になるテーマをタップ。もう一度タップで外せます（{form.recentInterests.length}件選択中）。
            </div>
          </div>
        </div>
        <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
          {INTERESTS.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`chip ${form.recentInterests.includes(opt) ? "on" : ""}`}
              onClick={() => toggleInterest(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </section>

      {/* 保存ゾーン（登録情報・出会いの幅・関心の変更をまとめて反映） */}
      <section className="page section">
        <div className="acct-savebox">
          <div className="asb-text">
            <div className="asb-title">編集した内容を保存</div>
            <div className="asb-sub">
              登録情報・新しい出会いの幅・いまの関心の変更を、まとめて反映します。
            </div>
          </div>
          <div className="asb-action">
            {savedMsg && <span className="acct-saved-msg">{savedMsg}</span>}
            <button type="button" className="btn btn--gold" onClick={onSave} disabled={saving}>
              {saving ? "更新中…" : "プロフィールを更新する"}
            </button>
          </div>
        </div>
      </section>
    </>
  );
}

export default function AccountPage() {
  const provider = useProvider();
  const router = useRouter();
  // Firebase Auth UID・email・displayName を取得。未ログイン or mock 時は DEMO_USER_ID にフォールバック
  const [uid, setUid] = useState<string | null>(null);
  const [authEmail, setAuthEmail] = useState<string | null>(null);
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => {
    setUid(u?.uid ?? null);
    setAuthEmail(u?.email ?? null);
    setAuthDisplayName(u?.displayName ?? null);
  }), []);
  const user = provider.getUser(uid ?? DEMO_USER_ID);

  const onLogout = async () => {
    await signOutUser();
    router.push("/login");
  };
  const total = provider.listBooks().filter((b) => b.shelf === "library").length;

  if (!user) {
    return (
      <>
        <Topbar greeting={<b>アカウント</b>} />
        <section className="page section">
          <div className="muted">{provider.ready ? "ユーザーが見つかりません。" : "読み込み中…"}</div>
        </section>
      </>
    );
  }

  // Firebase Auth の displayName を優先し、Firestore name をフォールバックにする。
  // 名前とメールが同じソース（Firebase Auth）から来るため常に一致する。
  const displayName = authDisplayName || user.name || "アカウント";
  const displayInitial = displayName[0] || "?";

  return (
    <>
      <Topbar greeting={<b>アカウント</b>} />

      <header className="acct-head page">
        <span className="acct-avatar">{displayInitial}</span>
        <div className="acct-headmeta">
          <span className="eyebrow">Your account</span>
          <h1 className="acct-name">{displayName}</h1>
          {authEmail && <div className="acct-role">{authEmail}</div>}
        </div>
        <div className="acct-stats">
          <Mini n={total} label="蔵書" />
          <Mini n={MOCK_HIGHLIGHTS.length} label="ハイライト" />
          <Mini n={0} label="お気に入り作家" />
        </div>
      </header>

      <ProfileEditor user={user} />

      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Connected sources</div>
            <div className="section-title">データ連携</div>
          </div>
        </div>
        <div className="acct-sources">
          {CONNECTED.map((s) => (
            <div key={s.name} className="acct-source panel">
              <span className="as-icon">{s.icon}</span>
              <span className="as-name">{s.name}</span>
              <span className="as-state">✓ 連携済み（デモ）</span>
            </div>
          ))}
        </div>
      </section>

      {/* ログアウト */}
      <section className="page section">
        <div className="acct-savebox">
          <div className="asb-text">
            <div className="asb-title">ログアウト</div>
            <div className="asb-sub">このデバイスのセッションを終了します。</div>
          </div>
          <div className="asb-action">
            <button type="button" className="btn" onClick={onLogout}>
              ログアウト
            </button>
          </div>
        </div>
      </section>
    </>
  );
}
