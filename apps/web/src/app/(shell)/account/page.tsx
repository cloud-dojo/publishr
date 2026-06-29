"use client";

import { useEffect, useState } from "react";
import type { User } from "@publishr/shared-schema";
import { useRouter } from "next/navigation";

import { ConnectSources } from "@/components/ConnectSources";
import { Topbar } from "@/components/shell/Topbar";
import { DEMO_USER_ID, canManualTrigger, dataSource } from "@/data/config";
import { useFavorites } from "@/data/favorites-store";
import { useActions, useProvider } from "@/data/hooks";
import { signOutUser, watchAuth } from "@/lib/firebase";
import { annotationsToHighlights, mergeHighlights } from "@/data/mock-highlights";
import {
  optionsFor,
  serendipityOptions,
  type InitialProfileInput,
} from "@/data/profileOptions";
import { getInitialProfile, saveInitialProfile } from "@/data/user-writes";

const INDUSTRY = optionsFor("industry");
const JOBTYPE = optionsFor("jobType");
const POSITION = optionsFor("position");
const INTERESTS = optionsFor("recentInterests");
const READING_GENRES = optionsFor("readingGenres");

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
  readingGenres: string[];
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
      readingGenres: saved.readingGenres ?? [],
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
    readingGenres: [],
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

  const toggleGenre = (opt: string) => {
    setForm((f) => ({
      ...f,
      readingGenres: f.readingGenres.includes(opt)
        ? f.readingGenres.filter((x) => x !== opt)
        : [...f.readingGenres, opt],
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
      readingGenres: form.readingGenres,
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

      {/* 好みの読み口・形態（初期設定で選んだ本のタイプ。ここで選び直せる） */}
      <section className="page section">
        <div className="section-head">
          <div>
            <div className="eyebrow">Your reading style</div>
            <div className="section-title">好みの読み口・形態</div>
            <div className="section-sub">
              どんな読み口の本が好みですか。タップで選択・解除できます（{form.readingGenres.length}件選択中）。
            </div>
          </div>
        </div>
        <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
          {READING_GENRES.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`chip ${form.readingGenres.includes(opt) ? "on" : ""}`}
              onClick={() => toggleGenre(opt)}
            >
              {opt}
            </button>
          ))}
        </div>
      </section>

      {/* 保存ゾーン（登録情報・出会いの幅・関心・読み口の変更をまとめて反映） */}
      <section className="page section">
        <div className="acct-savebox">
          <div className="asb-text">
            <div className="asb-title">編集した内容を保存</div>
            <div className="asb-sub">
              登録情報・新しい出会いの幅・いまの関心・好みの読み口の変更を、まとめて反映します。
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
  const actions = useActions();
  const router = useRouter();
  // Firebase Auth UID・email・displayName を取得。未ログイン or mock 時は DEMO_USER_ID にフォールバック
  const [uid, setUid] = useState<string | null>(null);
  const [authEmail, setAuthEmail] = useState<string | null>(null);
  const [authDisplayName, setAuthDisplayName] = useState<string | null>(null);
  // 実行中の企画種別（"honmei" | "serendipity" | null）。種別ごとにボタンを個別に無効化する。
  const [triggering, setTriggering] = useState<string | null>(null);
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null);
  useEffect(() => watchAuth((u) => {
    setUid(u?.uid ?? null);
    setAuthEmail(u?.email ?? null);
    setAuthDisplayName(u?.displayName ?? null);
  }), []);
  const user = provider.getUser(uid ?? DEMO_USER_ID);

  // 既存ユーザー（first-run 済み）が UI から企画を再実行する導線（prod-live-followups #7）。
  // themeKind=honmei は本命テーマ、serendipity は隣接/反対/飛躍/ニッチの出会い枠。
  const onTriggerPlanning = async (themeKind: "honmei" | "serendipity") => {
    setTriggering(themeKind);
    setTriggerMsg(null);
    const label = themeKind === "serendipity" ? "新しい出会いの企画" : "本命の企画";
    try {
      await actions.runPipeline(uid ?? DEMO_USER_ID, themeKind);
      setTriggerMsg(`${label}を実行しました。書店に反映されるまで少し待ってください。`);
    } catch (err) {
      console.error(err);
      setTriggerMsg(`${label}に失敗しました。少し待ってから再実行してください。`);
    } finally {
      setTriggering(null);
    }
  };
  const onLogout = async () => {
    await signOutUser();
    router.push("/login");
  };
  // 蔵書＝ユーザーが「書庫へ移動」した本（書庫ページと一致＝published かつ shelf==="library"）。
  const total = provider
    .listBooks()
    .filter((b) => b.status === "published" && b.shelf === "library").length;
  // ハイライト数：ハイライト画面(visibleItems)と完全に同じソース・同じ除外条件で数える
  // （note=付箋は表示しないので集計からも除外）。account 8 vs 画面 6 の食い違いを解消。
  const highlightCount = mergeHighlights(
    annotationsToHighlights(provider.listBooks()),
    dataSource === "mock"
  ).filter((h) => h.kind !== "note").length;
  // お気に入り作家数：お気に入りストア（localStorage＋Firestore）の実数。
  const favoriteCount = useFavorites().size;

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
          <Mini n={highlightCount} label="ハイライト" />
          <Mini n={favoriteCount} label="お気に入り作家" />
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
        <ConnectSources initial={user.connectedSources} />
      </section>

      {/* 方針A（prod-live-followups #7）: 「今すぐ企画」は実 Vertex 企画＝課金を発火するため、
          allowlist 一致の uid（＝デモの佐倉）にのみ表示する。バックエンドの ALLOWED_TRIGGER_UIDS
          が実際のガード（一般ユーザーは 403）で、ここは UI を見せない側の多層防御。 */}
      {dataSource !== "mock" && canManualTrigger(uid) && (
        <section className="page section">
          <div className="acct-savebox">
            <div className="asb-text">
              <div className="asb-title">今すぐ企画</div>
              <div className="asb-sub">
                週次バッチを待たずに、あなた向けの企画を手動で実行します。本命はいまの関心の中心から、
                新しい出会いは少し離れたテーマから本を仕立てます。生成には数分かかります。
              </div>
            </div>
            <div className="asb-action">
              {triggerMsg && <span className="acct-saved-msg">{triggerMsg}</span>}
              <button
                type="button"
                className="btn btn--gold"
                onClick={() => onTriggerPlanning("honmei")}
                disabled={triggering !== null}
              >
                {triggering === "honmei" ? "企画中..." : "本命を企画"}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => onTriggerPlanning("serendipity")}
                disabled={triggering !== null}
              >
                {triggering === "serendipity" ? "企画中..." : "新しい出会いを企画"}
              </button>
            </div>
          </div>
        </section>
      )}

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


