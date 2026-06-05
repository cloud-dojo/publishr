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
