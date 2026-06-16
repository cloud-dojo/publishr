"""C4結線: モードA v2出力 → shared-schema Book/Persona マッピングのテスト（決定的）。

run_mode_a の (plan, shelved, personas) を、書店UIが読む Book(arrivals/draft)＋Persona に
変換する純粋マッパーを検証する。正本: docs/design/api-contract.md / agent-io-contract.md §5-2a。
"""

from __future__ import annotations

from publishr_schema import Book, GeneratedPersona, Persona, PlanProposal

from publishr_agents.persist_mapping import map_mode_a_to_books


def _plan() -> PlanProposal:
    return PlanProposal.model_validate(
        {
            "proposalId": "plan_arr_01",
            "themeKind": "honmei",
            "round": 2,
            "tentativeTitle": "任せ方の設計図",
            "readerSituation": "新任2ヶ月",
            "whyNowForYou": "6/5役員報告を控える今",
            "coreMessage": "任せ方を型に",
            "diffFromMarket": "新任×年上実力者に限定",
        }
    )


def _personas() -> list[GeneratedPersona]:
    return [
        GeneratedPersona(
            persona_id="p1", name="神崎 玄一郎", voice_style="ロジカル・構造化",
            format="ストレートな自己啓発書", persona="元事業部長。権限を表で設計する。",
            expertise=["組織設計", "権限委譲"], from_favorite=False, ephemeral=True,
        ),
        GeneratedPersona(
            persona_id="p2", name="里見 ほたる", voice_style="感覚的・情緒的",
            format="小説・物語形式", persona="元百貨店フロア長から作家へ。",
            expertise=["現場マネジメント"], from_favorite=False, ephemeral=True,
        ),
    ]


def _shelved() -> list[dict]:
    def book(pid, title, variant, url):
        return {
            "personaId": pid,
            "bookDraft": {
                "title": title, "subtitle": "サブ",
                "deliveryReason": "観測から…という局面が見えたため。",
                "problemToSolve": "年上部下の任せ方", "coreMessage": "型を持つ",
                "agenda": [{"chapter": "第1章", "summary": "現状"}, {"chapter": "第2章", "summary": "型"}],
                "prefaceSample": "はじめに…",
            },
            "verdict": {"round": 1, "score": 62, "decision": "approve"},
            "editRounds": 1, "coverVariant": variant, "coverPrompt": "Minimalist...", "coverUrl": url,
        }
    return [
        book("p1", "任せ方の設計図（神崎）", "b1", None),
        book("p2", "任せ方の設計図（里見）", "b2", ".dev-logs/covers/book_p2.png"),
    ]


def test_maps_one_book_per_shelved():
    books, personas = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x")
    assert len(books) == 2
    assert all(isinstance(b, Book) for b in books)


def test_books_land_in_arrivals_as_draft_owned():
    books, _ = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x")
    for b in books:
        assert b.shelf == "arrivals"
        assert b.status == "draft"
        assert b.owner_uid == "u_x"
        assert b.kind == "honmei"
        assert b.plan_id == "plan_arr_01"


def test_book_carries_detail_and_cover():
    books, _ = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x")
    b0 = books[0]
    assert b0.title == "任せ方の設計図（神崎）"
    assert b0.delivery_reason  # 入荷理由（UIの reason フォールバック）
    assert b0.problem_to_solve and b0.core_message and b0.preface_sample
    assert b0.cover_variant == "b1"
    assert b0.agenda and b0.agenda[0].title == "第1章" and b0.agenda[0].desc == "現状"
    # cover_url は埋まる本もある
    assert books[1].cover_url == ".dev-logs/covers/book_p2.png"


def test_author_persona_resolvable():
    books, personas = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x")
    pmap = {p.id: p for p in personas}
    for b in books:
        assert b.author_persona_id in pmap  # 著者名が引ける（UI getPersona）
    assert all(isinstance(p, Persona) for p in personas)
    p1 = pmap["0_p1"]  # persona ID は run トークン付き（created_at 未指定→"0"）
    assert p1.name == "神崎 玄一郎"
    assert p1.persona.career  # PersonaDetail 必須が埋まる
    assert p1.voice_style == "ロジカル・構造化"
    assert p1.ephemeral is True


def test_books_and_personas_validate_as_schema():
    books, personas = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x")
    for b in books:
        Book.model_validate(b.model_dump(by_alias=True))
    for p in personas:
        Persona.model_validate(p.model_dump(by_alias=True))


def test_created_at_is_threaded():
    books, _ = map_mode_a_to_books(
        _plan(), _shelved(), _personas(), owner_uid="u_x", created_at="2026-06-08T06:00:00+09:00"
    )
    assert all(b.created_at == "2026-06-08T06:00:00+09:00" for b in books)


def test_does_not_mutate_input():
    shelved = _shelved()
    before = shelved[0]["bookDraft"]["title"]
    map_mode_a_to_books(_plan(), shelved, _personas(), owner_uid="u_x")
    assert shelved[0]["bookDraft"]["title"] == before


def test_book_ids_unique_per_run():
    """同じ created_at（＝同一runの再処理）は同一ID（冪等）、別 created_at（＝別run）は別ID
    （上書きせず書庫に積み上がる）。"""
    t1 = "2026-06-16T06:00:00+09:00"
    t2 = "2026-06-17T06:00:00+09:00"
    a, _ = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x", created_at=t1)
    a2, _ = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x", created_at=t1)
    b, _ = map_mode_a_to_books(_plan(), _shelved(), _personas(), owner_uid="u_x", created_at=t2)
    assert [x.id for x in a] == [x.id for x in a2]  # 同一run（同 created_at）＝同一ID（再処理冪等）
    assert {x.id for x in a}.isdisjoint({x.id for x in b})  # 別run＝別ID＝積み上げ（上書きしない）
    assert all(x.id.startswith("arr_") for x in a)  # 既存 b_*/_sakura と衝突しない接頭辞


def test_limit_consistency_only_used_personas_mapped():
    # shelved が1冊だけなら persona も1人だけ返す
    one = _shelved()[:1]
    books, personas = map_mode_a_to_books(_plan(), one, _personas(), owner_uid="u_x")
    assert len(books) == 1
    assert {p.id for p in personas} == {"0_p1"}  # run トークン付き（created_at 未指定→"0"）
