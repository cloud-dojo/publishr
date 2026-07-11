"""パイプラインのセッション状態キー（ctx.session.state）。"""

USER_ID = "user_id"
OBSERVATION = "observation"
READER_PROFILE = "reader_profile"
CAND_PREFIX = "cand_"  # cand_practical / cand_framework / cand_contrarian
CANDIDATES = "candidates"
REJECT_LOG = "reject_log"
APPROVED_PLAN_IDS = "approved_plan_ids"
BOOKS = "books"

# ── v2（vertex）パイプライン state キー（P0bシーム・mock経路では未使用）──
# 値は camelCase。プロンプトの {{var}} 名と一致させる。
THEME_KIND = "themeKind"
ROUND = "round"
SUB_READER_CONTEXT = "subReaderContext"
SUB_MARKET = "subMarket"
SUB_THEME_INSIGHT = "subThemeInsight"
PLAN_DRAFT = "planDraft"
LEADER_VERDICT = "leaderVerdict"
REJECTION_FEEDBACK = "rejectionFeedback"
APPROVED_PLAN = "approvedPlan"
GENERATED_PERSONA_SET = "generatedPersonaSet"
EDITOR_VERDICT = "editorVerdict"
EDITOR_FEEDBACK = "editorFeedback"

# ── v3（4テーマ束ね・1-1-1-1配本・2026-06-23 予約制廃止改定）state キー ──
EDITORIAL_INTENT = "editorialIntent"        # STEP2-0 編集意図（編集長）
THEME_ASSIGNMENT_SET = "themeAssignmentSet"  # STEP2-0 編集長テーマ設定（4チーム割当）
SUB_TREND = "subTrend"                       # STEP2c-1 トレンド調査（今・時間軸）
PLAN_SET = "planSet"                         # STEP2 配本セット（4テーマ→4冊）
PLAN_SET_VERDICT = "planSetVerdict"          # STEP2 編集長セットゲート（ポートフォリオ採点）
AUTHOR_CASTING = "authorCasting"             # STEP3 著者キャスティング（候補3→選抜1）
SERENDIPITY_SET = "serendipitySet"           # セレンディピティ別ロジック（4テーマ→4冊）
