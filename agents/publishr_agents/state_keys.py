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
# 値は camelCase。プロンプトの {{var}} 名・docs/design/adk-control-flow.md §4 と一致させる。
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

# ── v3（3テーマ束ね・2-2-1配本・2026-06-14）state キー ──
EDITORIAL_INTENT = "editorialIntent"   # STEP2-0 編集意図
PLAN_SET = "planSet"                    # STEP2b 配本セット（3テーマ→5冊）
PLAN_SET_VERDICT = "planSetVerdict"     # STEP2a ポートフォリオ採点
SERENDIPITY_SET = "serendipitySet"      # セレンディピティ別ロジック（5テーマ→5冊）
