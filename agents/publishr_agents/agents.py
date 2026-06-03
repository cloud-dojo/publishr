"""ADK カスタムエージェント群（企画会議パイプライン）。

各エージェントは BaseAgent を継承し、ctx.session.state を読み書きしつつ
Event(state_delta) を yield する。MVPでは出力は決定的キャンド。"""

from __future__ import annotations

from typing import AsyncGenerator, Optional

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from . import canned
from . import state_keys as K


def _emit(author: str, state_delta: dict) -> Event:
    return Event(author=author, actions=EventActions(state_delta=state_delta))


class ObserveAgent(BaseAgent):
    """STEP0: Keepメモを観測・集計（非エージェント的バッチ処理）。"""

    user_id: str

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        observation = canned.aggregate_keep_notes(self.user_id)
        ctx.session.state[K.USER_ID] = self.user_id
        ctx.session.state[K.OBSERVATION] = observation
        yield _emit(self.name, {K.USER_ID: self.user_id, K.OBSERVATION: observation})


class ReaderAgent(BaseAgent):
    """STEP1: 観測から Reader Profile を確定。"""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        user = canned.get_user(ctx.session.state.get(K.USER_ID))
        observation = ctx.session.state.get(K.OBSERVATION, {})
        profile = canned.build_reader_profile(user, observation)
        ctx.session.state[K.READER_PROFILE] = profile
        yield _emit(self.name, {K.READER_PROFILE: profile})


class PlanningAgent(BaseAgent):
    """STEP2: 永続ペルソナで条件付けされた1企画者。並列実行される。"""

    persona_key: str
    persona_label: str
    candidate: str
    plan_id: Optional[str] = None

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        key = K.CAND_PREFIX + self.persona_key
        value = {
            "key": self.persona_key,
            "persona": self.persona_label,
            "candidate": self.candidate,
            "planId": self.plan_id,
        }
        ctx.session.state[key] = value
        yield _emit(self.name, {key: value})


class SelectionGateAgent(BaseAgent):
    """STEP2: 企画リーダー＝選抜ゲート（対立①）。全却下→再提出→採否確定。"""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        # 並列で出そろった候補を確認（再現可能な視点が3つ揃っているか）
        proposed = canned.normalize_candidates([
            ctx.session.state[k]
            for k in ctx.session.state.keys()
            if k.startswith(K.CAND_PREFIX)
        ])
        reject_log_entries = canned.selection_reject_log(proposed)
        approved = canned.approved_plan_ids(proposed, reject_log_entries)
        candidates = [c.model_dump(by_alias=True) for c in proposed]
        reject_log = [e.model_dump(by_alias=True) for e in reject_log_entries]
        ctx.session.state[K.CANDIDATES] = candidates
        ctx.session.state[K.REJECT_LOG] = reject_log
        ctx.session.state[K.APPROVED_PLAN_IDS] = approved
        yield _emit(
            self.name,
            {
                K.CANDIDATES: candidates,
                K.REJECT_LOG: reject_log,
                K.APPROVED_PLAN_IDS: approved,
                "candidate_count": len(proposed),
            },
        )


class AuthorAgendaAgent(BaseAgent):
    """STEP3: 採用企画に対し、作家ペルソナの文体で序文＋アジェンダを生成（=入荷書籍）。"""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        approved = ctx.session.state.get(K.APPROVED_PLAN_IDS, [])
        books = [b.model_dump(by_alias=True) for b in canned.arrival_books(approved)]
        ctx.session.state[K.BOOKS] = books
        yield _emit(self.name, {K.BOOKS: books})


class CoverAgent(BaseAgent):
    """STEP4: 装丁（Imagen代替）。coverVariant は各書籍に付与済みのため確認のみ。"""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        books = ctx.session.state.get(K.BOOKS, [])
        yield _emit(self.name, {"covers_assigned": len(books)})
