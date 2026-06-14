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


# ── STEP3 persona: 員数5・2軸分散・薄さ・fromFavorite・人物名衝突 ──────────
def _good_personas() -> dict:
    """voiceStyle×format が5通りユニーク・persona がリッチ・衝突名なしの正例。"""
    bodies = [
        ("結城 遼太", "ロジカル・構造化", "ストレートな自己啓発書",
         "元・大手電機メーカーの事業部長。30名の組織を任され半年で離職を3名出した原体験を持つ。口癖は『で、それは誰の意思決定？』。感情論を嫌い必ず構造に落とす。"),
        ("葉山 みのり", "感覚的・情緒的", "小説・物語形式",
         "元・地方百貨店の婦人服フロア長から作家へ転じた。年上のベテラン販売員に囲まれ若くして売場を任された日々を一人称の物語に書く。信条は『正しさより、まず隣に立つ』。"),
        ("桐谷 学", "学術的", "対話・問答形式",
         "大学で組織論を講じる研究者。学説を一方的に説かず問いを重ねて読者自身に発見させる対話を好む。『なぜそう言えるのか』を必ず問い返すのが口癖。"),
        ("梶原 鉄平", "泥臭い・現場", "エッセイ形式",
         "町工場の叩き上げ工場長を30年。現場の油と汗の手触りでしか語れないと信じ、理論より一つの失敗談を出す。出身は中卒、夜間高校を経て独学で学んだ。"),
        ("東堂 静観", "思想的・哲学的", "対話・問答形式",
         "東洋思想を学びリーダー論に接続する元・僧侶。答えを与えず問答で迷いを解く。『主人公は誰か』が口癖で、原体験は寺の世代交代にある。"),
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
        "reason": "voiceStyle×format を5通りに散らし、読者の実務的嗜好へ主軸を寄せた",
    }


def test_good_persona_set_passes():
    rep = sd.run_discipline_checks("persona_generator", _good_personas())
    assert rep.schema_ok is True
    assert rep.violations == []
    assert rep.metrics.get("axisUnique") == "5/5"


def test_persona_count_not_five_violation():
    raw = _good_personas()
    raw["personas"] = raw["personas"][:4]  # 4人に削る
    rep = sd.run_discipline_checks("persona_generator", raw)
    assert any("員数が5人でない" in v for v in rep.violations)


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
    assert rep.metrics.get("fromFavoriteAdopted") == "1/5"


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
