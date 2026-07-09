"""scripts/smoke_discipline.py の決定的テスト（オフライン・$0）。

良い被験者出力＝違反なし、意図的に壊した出力＝確定違反を検出することを回す。
正本: docs/planning（プロンプト改修インナーループ）。scripts は testpaths 外のため
ここ（apps/api/tests）に置いて make verify(pytest) で拾わせる。
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SPEC = importlib.util.spec_from_file_location("smoke_discipline", ROOT / "scripts" / "smoke_discipline.py")
assert SPEC and SPEC.loader
sd = importlib.util.module_from_spec(SPEC)
sys.modules["smoke_discipline"] = sd  # @dataclass の module 解決（Py3.14）に必要
SPEC.loader.exec_module(sd)

FIXTURES = ROOT / "packages" / "shared-schema" / "fixtures" / "plan_proposals"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ── schema 汚染（フィールド名創作） ─────────────────────────
def test_unknown_field_detected_on_sub_reader_context():
    raw = {
        "theme": "x",
        "concreteTroublePoints": ["創作フィールド"],  # 正: painPoints
        "decisions": [],
        "evidence": [],
    }
    rep = sd.run_discipline_checks("sub_reader_context", raw)
    assert "concreteTroublePoints" in rep.unknown_fields
    assert rep.has_violations is True


def test_role_overreach_flag_on_sub_market():
    raw = {
        "theme": "x", "queries": ["q"],
        "findings": [{"title": "実在書", "point": "論点", "source": "https://example.com"}],
        "marketGap": "本書は超訳でハウツー化した実用書にすべき",  # 越境
    }
    rep = sd.run_discipline_checks("sub_market", raw)
    assert rep.schema_ok is True  # スキーマ自体は通る
    assert any("role越境" in f for f in rep.flags)


def test_clean_sub_market_no_violation():
    raw = {
        "theme": "x", "queries": ["q1"],
        "findings": [{"title": "国家はなぜ衰退するのか", "point": "制度論", "source": "https://example.com/a"}],
        "marketGap": "マクロ制度論に偏り、ミドル層向けが手薄",
    }
    rep = sd.run_discipline_checks("sub_market", raw)
    assert rep.schema_ok is True
    assert rep.violations == []


# ── plan_owner: 良fixture は違反なし ─────────────────────────
def test_good_owner_fixture_passes():
    plan = _load("u_sakura_honmei.json")
    # fixture は _meta 等を含むので、PlanProposal フィールドのみ raw に整形不要（extra=ignoreで通る）
    rep = sd.run_discipline_checks("plan_owner", plan)
    assert rep.schema_ok is True
    assert rep.violations == []  # 8項目充足・スキーマ健全


def test_owner_missing_required_field():
    plan = _load("u_sakura_honmei.json")
    plan = dict(plan)
    plan["coreMessage"] = ""  # 必須を空に
    rep = sd.run_discipline_checks("plan_owner", plan)
    assert any("core_message" in v for v in rep.violations)


def test_serendipity_owner_shelf_grammar_flag():
    plan = _load("u_sakura_serendipity.json")
    plan = dict(plan)
    plan["whyNowForYou"] = "あなたの課題である年上部下の悩みをすぐ使えるハウツーで解決します"
    rep = sd.run_discipline_checks("plan_owner", plan, context={"theme_kind": "serendipity"})
    assert any("棚書き文法違反" in f or "ハウツー化" in f for f in rep.flags)


def test_fewshot_contamination_metric_present():
    plan = _load("u_sakura_honmei.json")
    rep = sd.run_discipline_checks("plan_owner", plan)
    assert "fewshotContamination" in rep.metrics
    assert 0.0 <= rep.metrics["fewshotContamination"] <= 1.0


# ── plan_leader: 採点自己整合・approvedPlan無改変 ──────────────
def _good_verdict() -> dict:
    plan = _load("u_sakura_honmei.json")
    bd = {"relevance": 25, "differentiation": 23, "researchUse": 24, "titleHook": 23}
    return {
        "round": 1, "score": sum(bd.values()), "scoreBreakdown": bd,
        "belowFloor": False, "decision": "approve",
        "rejectionFeedback": None, "approvedPlan": plan,
    }


def test_leader_consistent_approve_no_violation():
    v = _good_verdict()
    plan = _load("u_sakura_honmei.json")
    rep = sd.run_discipline_checks("plan_leader", v, context={"input_plan": plan})
    assert rep.violations == []


def test_leader_sum_mismatch_violation():
    v = _good_verdict()
    v["score"] = 99  # 4観点和(95)と不一致
    rep = sd.run_discipline_checks("plan_leader", v)
    assert any("自己整合" in x for x in rep.violations)


def test_leader_approved_plan_tampered_violation():
    v = _good_verdict()
    plan = _load("u_sakura_honmei.json")
    v["approvedPlan"] = dict(v["approvedPlan"])
    v["approvedPlan"]["tentativeTitle"] = "leaderが勝手に書き換えたタイトル"
    rep = sd.run_discipline_checks("plan_leader", v, context={"input_plan": plan})
    assert any("approvedPlan.tentativeTitle" in x for x in rep.violations)


# ── reader_analyst: evidence 接地 ───────────────────────────
def test_reader_analyst_unbound_challenges_violation():
    raw = {
        "base": {},
        "currentWork": {"challenges": ["何かに悩む"], "evidence": []},
        "readingBehavior": {},
    }
    rep = sd.run_discipline_checks("reader_analyst", raw)
    assert any("evidence" in v for v in rep.violations)


# ── STEP3 persona: 員数4（1人/冊・1-1-1-1）・2軸分散・薄さ・fromFavorite・人物名衝突 ──────────
def _good_personas() -> dict:
    """voiceStyle×format が4通りユニーク・persona がリッチ・衝突名なしの正例（4テーマ＝4冊）。"""
    bodies = [
        ("結城 遼太", "ロジカル・構造化", "ストレートな自己啓発書",
         "元・大手電機メーカーの事業部長。30名の組織を任され半年で離職を3名出した原体験を持つ。口癖は『で、それは誰の意思決定？』。感情論を嫌い必ず構造に落とす。"),
        ("葉山 みのり", "感覚的・情緒的", "小説・物語形式",
         "元・地方百貨店の婦人服フロア長から作家へ転じた。年上のベテラン販売員に囲まれ若くして売場を任された日々を一人称の物語に書く。信条は『正しさより、まず隣に立つ』。"),
        ("桐谷 学", "学術的", "対話・問答形式",
         "大学で組織論を講じる研究者。学説を一方的に説かず問いを重ねて読者自身に発見させる対話を好む。『なぜそう言えるのか』を必ず問い返すのが口癖。"),
        ("梶原 鉄平", "泥臭い・現場", "エッセイ形式",
         "町工場の叩き上げ工場長を30年。現場の油と汗の手触りでしか語れないと信じ、理論より一つの失敗談を出す。出身は中卒、夜間高校を経て独学で学んだ。"),
    ]
    return {
        "planId": "plan_test", "themeKind": "honmei",
        "personas": [
            {
                "personaId": f"p{i+1}", "name": nm, "voiceStyle": vs, "format": fmt,
                "persona": body, "expertise": ["組織"], "pastBooks": [],
                "fromFavorite": False, "ephemeral": True,
            }
            for i, (nm, vs, fmt, body) in enumerate(bodies)
        ],
        "reason": "voiceStyle×format を4通りに散らし、読者の実務的嗜好へ主軸を寄せた",
    }


def test_good_persona_set_passes():
    rep = sd.run_discipline_checks("persona_generator", _good_personas())
    assert rep.schema_ok is True
    assert rep.violations == []
    assert rep.metrics.get("axisUnique") == "4/4"


def test_persona_count_not_four_violation():
    raw = _good_personas()
    raw["personas"] = raw["personas"][:3]  # 3人に削る（員数4厳守違反）
    rep = sd.run_discipline_checks("persona_generator", raw)
    assert any("員数が4人でない" in v for v in rep.violations)


def test_persona_axis_not_distributed_violation():
    raw = _good_personas()
    # p2 を p1 と同じ voiceStyle×format に揃える＝組み合わせ重複
    raw["personas"][1]["voiceStyle"] = raw["personas"][0]["voiceStyle"]
    raw["personas"][1]["format"] = raw["personas"][0]["format"]
    rep = sd.run_discipline_checks("persona_generator", raw)
    assert any("2軸分散していない" in v for v in rep.violations)


def test_persona_thin_flag():
    raw = _good_personas()
    raw["personas"][0]["persona"] = "経営に詳しい。"  # 薄い
    rep = sd.run_discipline_checks("persona_generator", raw)
    assert any("persona が薄い" in f for f in rep.flags)


def test_from_favorite_without_favorites_violation():
    raw = _good_personas()
    raw["personas"][0]["fromFavorite"] = True  # お気に入り空なのに採用主張
    rep = sd.run_discipline_checks("persona_generator", raw)  # context 無し＝favs空
    assert any("favoriteAuthors が空なのに fromFavorite=true" in v for v in rep.violations)


def test_from_favorite_with_favorites_metric_no_violation():
    raw = _good_personas()
    raw["personas"][0]["fromFavorite"] = True
    favs = [{"personaId": "f1", "name": "架空の師匠", "voiceStyle": "ロジカル", "format": "自己啓発"}]
    rep = sd.run_discipline_checks("persona_generator", raw, context={"favorite_authors": favs})
    assert all("fromFavorite=true" not in v for v in rep.violations)
    assert rep.metrics.get("fromFavoriteAdopted") == "1/4"


def test_known_name_collision_flag():
    raw = _good_personas()
    raw["personas"][0]["name"] = "神崎 玄一郎"  # step3 few-shot 例の著者名
    rep = sd.run_discipline_checks("persona_generator", raw)
    assert any("既知人物名との衝突" in f for f in rep.flags)


def test_fewshot_surname_leak_flag():
    # few-shot 例「里見ほたる」の姓だけ流用（「里見ほのか」）も検出する
    raw = _good_personas()
    raw["personas"][0]["name"] = "里見 ほのか"
    rep = sd.run_discipline_checks("persona_generator", raw)
    assert any("既知人物名との衝突" in f for f in rep.flags)


# ── STEP3 author_casting（4テーマ）: 候補3・chosen整合・選抜証跡 ──────────
def _good_casting() -> dict:
    """candidates が3通りユニーク・chosen が候補の1人・選抜理由ありの正例。"""
    cands = [
        {"personaId": "c1", "name": "結城 遼太", "voiceStyle": "ロジカル・構造化", "format": "ストレートな自己啓発書",
         "persona": "元・事業部長。30名を任され離職3名を出した原体験を持つ。口癖は『で、それは誰の意思決定？』。", "expertise": ["組織"], "pastBooks": [], "fromFavorite": False, "ephemeral": True},
        {"personaId": "c2", "name": "葉山 みのり", "voiceStyle": "感覚的・情緒的", "format": "小説・物語形式",
         "persona": "元・百貨店フロア長から作家へ。年上の販売員に囲まれ若くして売場を任された日々を物語に書く。信条は『正しさより隣に立つ』。", "expertise": ["接客"], "pastBooks": [], "fromFavorite": False, "ephemeral": True},
        {"personaId": "c3", "name": "梶原 鉄平", "voiceStyle": "泥臭い・現場", "format": "エッセイ形式",
         "persona": "町工場の叩き上げ工場長を30年。理論より一つの失敗談を出す。出身は中卒、夜間高校を経て独学で学んだ。", "expertise": ["製造"], "pastBooks": [], "fromFavorite": False, "ephemeral": True},
    ]
    return {"planId": "plan_test", "candidates": cands, "chosen": dict(cands[0]),
            "selectionReason": "bookRole=ハンドブックと読者の論理志向に最も合うため、他2候補でなくc1を選んだ"}


def test_good_casting_passes():
    rep = sd.run_discipline_checks("author_casting", _good_casting())
    assert rep.schema_ok is True
    assert rep.violations == []
    assert rep.metrics.get("axisUnique") == "3/3"


def test_casting_candidate_count_violation():
    raw = _good_casting()
    raw["candidates"] = raw["candidates"][:2]  # 候補2人（員数3違反）
    raw["chosen"] = dict(raw["candidates"][0])
    rep = sd.run_discipline_checks("author_casting", raw)
    assert any("候補員数が3人でない" in v for v in rep.violations)


def test_casting_chosen_mismatch_violation():
    raw = _good_casting()
    raw["chosen"] = dict(raw["chosen"]); raw["chosen"]["personaId"] = "cX"  # 候補に無いID
    rep = sd.run_discipline_checks("author_casting", raw)
    assert any("chosen.personaId が candidates に無い" in v for v in rep.violations)


def test_casting_missing_selection_reason_violation():
    raw = _good_casting()
    raw["selectionReason"] = ""  # 証跡なし
    rep = sd.run_discipline_checks("author_casting", raw)
    assert any("selectionReason が空" in v for v in rep.violations)


# ── serendipity_themes: 員数4・adjacency分散・棚書き文法 ──────────
def _good_serendipity() -> dict:
    return {
        "themes": [
            {"name": "指揮者はなぜ一言も発さず100人を束ねるのか", "adjacency": "隣接",
             "whyForReader": "率いるという関心の隣で、言葉を使わず束ねる所作を覗くと別の語彙が手に入る。"},
            {"name": "あえて指示しない――女将の察しの場づくり", "adjacency": "反対",
             "whyForReader": "細かく命じる通念の逆側に触れ、自分の率い方を相対化する余白が生まれる。"},
            {"name": "南極で28人を生きて連れ帰った男・シャクルトン", "adjacency": "飛躍",
             "whyForReader": "現代のオフィスから氷の海へ跳ぶ越境が、束ねることの根への想像を広げる。"},
            {"name": "棋士はなぜ負けた直後に感想戦をするのか", "adjacency": "ニッチ",
             "whyForReader": "負けをその場で言葉にする一点の作法が、内省への静かな関心に接続する。"},
        ],
        "reason": "隣接/反対/飛躍/ニッチで領域・時代を散らし、潜在関心に課題直撃せず接続した",
    }


def test_good_serendipity_passes():
    rep = sd.run_discipline_checks("serendipity_themes", _good_serendipity())
    assert rep.schema_ok is True
    assert rep.violations == []
    assert rep.metrics.get("adjacencyUnique") == "4/4"


def test_serendipity_adjacency_not_distributed_flag():
    raw = _good_serendipity()
    for t in raw["themes"]:
        t["adjacency"] = "隣接"  # 全部同じ＝非分散
    rep = sd.run_discipline_checks("serendipity_themes", raw)
    assert any("adjacency" in f and "分散していない" in f for f in rep.flags)


def test_serendipity_shelf_grammar_flag():
    raw = _good_serendipity()
    raw["themes"][0]["whyForReader"] = "あなたの課題をすぐ使えるハウツーで解決する"
    rep = sd.run_discipline_checks("serendipity_themes", raw)
    assert any("棚書き文法違反" in f for f in rep.flags)
    assert any("ハウツー化" in f for f in rep.flags)


# ── editor_chief_themes serendipity（live の日曜セレンディピティ本ゲート）: 距離不足・回収癖 ──
def _good_ect_serendipity() -> dict:
    return {
        "themeKind": "serendipity",
        "editorialIntent": {
            "shelfConcept": "未完成や偶然に惹かれる心を入口に、業務とは独立した知的主題から世界を眺め直す棚",
            "readerExperience": "効率とは別の物差しを一つ受け取り、世界の解像度が一段上がる静かな高揚が残る",
            "antiDuplication": ["業務課題を主題にも背景にも持ち込まない"],
            "balanceConstraints": ["領域を芸術・自然科学・歴史・哲学へ分散させる"],
        },
        "assignments": [
            {"teamId": "A", "theme": {"name": "なぜ廃墟や未完の建築は人の心を掴むのか", "role": "隣接探索",
              "targetReader": "途中の風景に惹かれた覚えのある人", "value": "未完成に宿る想像の余白という美意識に触れる", "forbiddenOverlap": "自然の造形は扱わない（B）"}},
            {"teamId": "B", "theme": {"name": "雪の結晶はなぜ二つと同じ形にならないのか", "role": "視座替え",
              "targetReader": "自然の細部に立ち止まる人", "value": "偶然と必然の絡みへの畏敬が深まる", "forbiddenOverlap": "人工物は扱わない（A）"}},
            {"teamId": "C", "theme": {"name": "金継ぎはなぜ割れた器の傷を金で目立たせるのか", "role": "ニッチ探索",
              "targetReader": "繕われた道具に愛着を覚える人", "value": "欠損を肯定するまなざしに出会う", "forbiddenOverlap": "建築は扱わない（A）"}},
            {"teamId": "D", "theme": {"name": "星の光が何万年も昔の姿で届くとき何を見ているのか", "role": "反対視点",
              "targetReader": "夜空に時間の遠さを感じた人", "value": "速さとは無縁の尺度を味わう", "forbiddenOverlap": "地上の話は扱わない（B・C）"}},
        ],
    }


def test_good_ect_serendipity_passes():
    rep = sd.run_discipline_checks(
        "editor_chief_themes", _good_ect_serendipity(), context={"theme_kind": "serendipity"}
    )
    assert rep.schema_ok is True
    assert rep.violations == []
    assert not any(("距離不足" in f) or ("回収癖" in f) for f in rep.flags)
    assert rep.metrics.get("roleUnique") == "4/4"


def test_ect_serendipity_taskword_in_name_flag():
    raw = _good_ect_serendipity()
    raw["assignments"][2]["theme"]["name"] = "大遠征が補給と納期の遅延をどう呑み込んだか"
    rep = sd.run_discipline_checks(
        "editor_chief_themes", raw, context={"theme_kind": "serendipity"}
    )
    assert any(("距離不足" in f) and ("偽装越境" in f) for f in rep.flags)


def test_ect_serendipity_reclaim_flag():
    raw = _good_ect_serendipity()
    raw["assignments"][0]["theme"]["value"] = "この学びは明日の業務にすぐ役立つ"
    rep = sd.run_discipline_checks(
        "editor_chief_themes", raw, context={"theme_kind": "serendipity"}
    )
    assert any("回収癖" in f for f in rep.flags)


def test_ect_serendipity_honmei_not_flagged():
    # honmei（context未指定）では editor_chief serendipity 固有チェックは走らない＝課題語名でもフラグ無し
    raw = _good_ect_serendipity()
    raw["themeKind"] = "honmei"
    raw["assignments"][0]["theme"]["name"] = "6/25更新までに導入効果を提案書のどこに組むか"
    rep = sd.run_discipline_checks("editor_chief_themes", raw)
    assert not any("偽装越境" in f for f in rep.flags)


# ── modeb_author 本文の抽象化（生情報＝固有の日付/実名/顧客名の漏れ検知） ──────────
def test_body_abstraction_clean_passes():
    body = "## 第4章\n経験豊富な年上の部下を例に考えよう。重要な報告を控えた局面では、説明責任が問われる。"
    rep = sd.run_discipline_checks("modeb_author", {"text": body}, context={"raw_terms": ["佐藤さん", "A社"]})
    assert rep.schema_ok is True
    assert not any("生情報漏れ" in f for f in rep.flags)
    assert rep.metrics.get("bodyChars", 0) > 0


def test_body_abstraction_date_flag():
    body = "6/5の役員報告であなたは説明責任を負えない。"
    rep = sd.run_discipline_checks("modeb_author", {"text": body}, context={})
    assert any("日付様トークン" in f for f in rep.flags)


def test_body_abstraction_name_flag():
    body = "佐藤さんに任せきれなかったA社案件を思い出してほしい。"
    rep = sd.run_discipline_checks(
        "modeb_author", {"text": body}, context={"raw_terms": ["佐藤さん", "A社"]}
    )
    assert any(("実名" in f) or ("顧客名" in f) for f in rep.flags)


# ── author_preview タイトルの分かりやすさ・簡潔さ（長さ＋問いかけ型 metric） ──────────
def test_title_concise_statement_passes():
    rep = sd.run_discipline_checks("author_preview", {"title": "年上の部下への、任せ方の設計図"})
    assert rep.schema_ok is True
    assert not any("長すぎ" in f for f in rep.flags)
    assert rep.metrics.get("titleForm") == "statement"


def test_title_too_long_flag():
    long_title = "あなたが初めて年上のベテラン部下を含むチームを率いるときに直面する、任せ方と線引きのすべて"
    rep = sd.run_discipline_checks("author_preview", {"title": long_title})
    assert any("長すぎ" in f for f in rep.flags)


def test_title_question_form_metric():
    rep = sd.run_discipline_checks("author_preview", {"title": "年上の部下に、どこまで任せますか？"})
    assert rep.metrics.get("titleForm") == "question"


# ── cover の3D/写実レンダー化検知（書店の本の装丁＝フラット2D） ──────────
def test_cover_flat_passes():
    cp = (
        "Flat 2D minimalist abstract geometric artwork. A single line-drawn diagram of nested rectangles. "
        "Calm off-white, navy accents, matte finish. No text, no lettering, no real faces, "
        "no 3D render, no isometric, no photorealistic product shot, no lorem ipsum."
    )
    rep = sd.run_discipline_checks("cover", {"coverPrompt": cp})
    assert rep.violations == []
    assert not any("3D/写実レンダー" in f for f in rep.flags)
    assert not any("文字/タイトル誘発" in f for f in rep.flags)


def test_cover_3d_render_flag():
    cp = (
        "An isometric 3D render of a glass cube on a circuit board with glowing cables, photorealistic. "
        "No text, no real faces."
    )
    rep = sd.run_discipline_checks("cover", {"coverPrompt": cp})
    assert any("3D/写実レンダー" in f for f in rep.flags)


def test_cover_texttrigger_flag():
    cp = "A modern editorial magazine layout book cover poster, abstract. No text, no real faces."
    rep = sd.run_discipline_checks("cover", {"coverPrompt": cp})
    assert any("文字/タイトル誘発" in f for f in rep.flags)


# ── STEP4 editor_preview（EditorVerdict・3観点） ──────────
def _good_editor_verdict() -> dict:
    bd = {"rawInsight": 21, "personaForward": 20, "catchiness": 19}
    return {
        "bookId": "book_test_p1", "round": 1, "score": sum(bd.values()),
        "scoreBreakdown": bd, "decision": "approve",
        "editorFeedback": "approve。次に上げるなら③タイトルの惹き。",
    }


def test_good_editor_preview_passes():
    rep = sd.run_discipline_checks("editor_preview", _good_editor_verdict())
    assert rep.schema_ok is True
    assert rep.violations == []


def test_editor_preview_approve_without_feedback_violation():
    v = _good_editor_verdict()
    v["editorFeedback"] = None  # approve でも feedback 必須（6/23校正・ラバースタンプ禁止）
    rep = sd.run_discipline_checks("editor_preview", v)
    assert any("ラバースタンプ" in x for x in rep.violations)


def test_editor_preview_sum_mismatch_violation():
    v = _good_editor_verdict()
    v["score"] = 75  # 3観点和(60)と不一致
    rep = sd.run_discipline_checks("editor_preview", v)
    assert any("3観点合計" in x for x in rep.violations)


# ── modeB modeb_editor（BodyVerdict・5観点） ──────────
def _good_body_verdict() -> dict:
    bd = {"coherence": 17, "hook": 16, "relevance": 18, "personaConsistency": 17, "actionability": 16}
    return {
        "score": sum(bd.values()), "scoreBreakdown": bd, "decision": "approve",
        "weakChapters": [], "editorFeedback": None,  # modeB は approve→null 許容
    }


def test_good_body_verdict_passes():
    rep = sd.run_discipline_checks("modeb_editor", _good_body_verdict())
    assert rep.schema_ok is True
    assert rep.violations == []


def test_body_verdict_sum_mismatch_violation():
    v = _good_body_verdict()
    v["score"] = 90  # 5観点和(84)と不一致
    rep = sd.run_discipline_checks("modeb_editor", v)
    assert any("本文5観点合計" in x for x in rep.violations)


def test_body_verdict_revise_without_feedback_violation():
    bd = {"coherence": 8, "hook": 6, "relevance": 4, "personaConsistency": 7, "actionability": 6}
    v = {"score": sum(bd.values()), "scoreBreakdown": bd, "decision": "revise",
         "weakChapters": [1], "editorFeedback": ""}
    rep = sd.run_discipline_checks("modeb_editor", v)
    assert any("editorFeedback が空" in x for x in rep.violations)


# ── STEP5 cover（coverPrompt・装丁メタ） ──────────
def _good_cover() -> dict:
    return {"bookId": "book_test_p1", "coverPrompt": (
        "A refined minimalist abstract artwork, contemporary fine-art print. "
        "A single navy motif on a calm off-white field resolving into a deep navy band across the lower third, "
        "subtle two-tone gradient with fine grain, generous negative space, muted professional palette, "
        "visual weight in the upper two-thirds. Completely text-free. "
        "No text, no lettering, no words, no logos, no real human faces, no 3D render, no isometric, "
        "no photorealistic product shot.")}


def test_good_cover_passes():
    rep = sd.run_discipline_checks("cover", _good_cover())
    assert rep.violations == []
    assert rep.metrics.get("premiumStyle") == "yes"
    assert not any("文字/タイトル誘発" in f for f in rep.flags)


def test_cover_missing_no_text_and_textburn_flag():
    c = _good_cover()
    c["coverPrompt"] = "A colorful cover with the title written in big gold letters, no real human faces."
    rep = sd.run_discipline_checks("cover", c)
    assert any("no-text" in x for x in rep.violations)
    assert any("焼き込み" in f for f in rep.flags)


# ── CLI ─────────────────────────────────────────────────
def test_main_returns_nonzero_on_violation(tmp_path):
    bad = {"theme": "x", "concreteTroublePoints": ["創作"], "decisions": [], "evidence": []}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    assert sd.main(["--role", "sub_reader_context", "--input", str(p)]) == 1


def test_main_returns_zero_on_clean(tmp_path):
    plan = _load("u_sakura_honmei.json")
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    assert sd.main(["--role", "plan_owner", "--input", str(p)]) == 0
