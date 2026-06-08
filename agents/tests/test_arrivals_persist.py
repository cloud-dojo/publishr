"""C4結線: arrivals 永続化（マッパー→RepositoryProtocol.upsert）のテスト（mock repo・決定的）。

run_mode_a 成果 → Book(arrivals/draft)＋Persona を mock リポジトリへ upsert し、書店UIが読む
クエリ（shelf=arrivals・status=draft）で取れる＆著者が解決できることを検証する。
"""

from __future__ import annotations

from publishr_schema import GeneratedPersona, PlanProposal

from publishr_agents.persist_mapping import map_mode_a_to_books, persist_arrivals
from publishr_api.repositories.mock_repository import MockRepository


def _inputs():
    plan = PlanProposal.model_validate(
        {
            "proposalId": "plan_arr_01", "themeKind": "honmei", "round": 2,
            "tentativeTitle": "任せ方の設計図", "readerSituation": "新任2ヶ月",
            "whyNowForYou": "6/5役員報告", "coreMessage": "型に", "diffFromMarket": "限定",
        }
    )
    personas = [
        GeneratedPersona(persona_id="p1", name="神崎 玄一郎", voice_style="ロジカル",
                         format="自己啓発", persona="元事業部長。", expertise=["組織"], ephemeral=True),
        GeneratedPersona(persona_id="p2", name="里見 ほたる", voice_style="情緒的",
                         format="小説", persona="元フロア長。", expertise=["現場"], ephemeral=True),
    ]
    shelved = [
        {"personaId": "p1", "bookDraft": {"title": "A", "deliveryReason": "DR-A", "coreMessage": "c",
         "agenda": [{"chapter": "第1章", "summary": "s"}], "prefaceSample": "p"},
         "verdict": {"round": 1, "score": 62, "decision": "approve"}, "editRounds": 1,
         "coverVariant": "b1", "coverPrompt": "x", "coverUrl": None},
        {"personaId": "p2", "bookDraft": {"title": "B", "deliveryReason": "DR-B", "coreMessage": "c",
         "agenda": [{"chapter": "第1章", "summary": "s"}], "prefaceSample": "p"},
         "verdict": {"round": 1, "score": 60, "decision": "approve"}, "editRounds": 1,
         "coverVariant": "b2", "coverPrompt": "x", "coverUrl": None},
    ]
    return plan, shelved, personas


def test_persist_arrivals_books_and_personas():
    plan, shelved, personas_in = _inputs()
    books, personas = map_mode_a_to_books(plan, shelved, personas_in, owner_uid="u_x")
    repo = MockRepository()

    n = persist_arrivals(repo, books, personas)
    assert n == len(books)

    # 書店UIの arrivals クエリで取れる
    arrivals = repo.list_books(status="draft", shelf="arrivals")
    ids = {b.id for b in arrivals}
    assert {"arr_p1", "arr_p2"} <= ids

    # 著者が解決できる（getPersona）
    for b in books:
        assert repo.get_persona(b.author_persona_id) is not None
    assert repo.get_persona("p1").name == "神崎 玄一郎"


def test_persist_is_idempotent():
    plan, shelved, personas_in = _inputs()
    books, personas = map_mode_a_to_books(plan, shelved, personas_in, owner_uid="u_x")
    repo = MockRepository()
    persist_arrivals(repo, books, personas)
    before = len(repo.list_books(status="draft", shelf="arrivals"))
    persist_arrivals(repo, books, personas)  # 同一IDで再upsert
    after = len(repo.list_books(status="draft", shelf="arrivals"))
    assert before == after  # 冪等（増えない）
