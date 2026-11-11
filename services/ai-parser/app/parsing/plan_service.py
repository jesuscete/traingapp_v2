import logging

from app.llm import factory
from app.llm.errors import LLMError
from app.parsing.plan import (
    generate_plan_with_llm,
    suggest_splits_with_llm,
)
from app.parsing.plan_stub import (
    generate_plan_stub,
    suggest_splits_stub,
)
from app.schemas.plan import (
    PlanGenerateIn,
    PlanResponse,
    SplitResponse,
    SportIn,
)

logger = logging.getLogger(__name__)


async def suggest_splits(
    sports: list[SportIn], gym_days: int
) -> SplitResponse:
    provider = factory.get_provider()
    if provider is None:
        return _splits_fallback(sports, gym_days)
    try:
        return await suggest_splits_with_llm(provider, sports, gym_days)
    except (LLMError, ValueError):
        logger.exception("LLM split suggestion failed (%s); using stub", provider.name)
        return _splits_fallback(sports, gym_days)


def _splits_fallback(sports: list[SportIn], gym_days: int) -> SplitResponse:
    return suggest_splits_stub(sports, gym_days).model_copy(update={"source": "fallback"})


def _plan_fallback(body: PlanGenerateIn) -> PlanResponse:
    plan = generate_plan_stub(body.sports, body.gym_days, body.split_id, body.goal, body.catalog)
    return plan.model_copy(update={"source": "fallback"})


async def generate_plan(body: PlanGenerateIn) -> PlanResponse:
    provider = factory.get_provider()
    if provider is None:
        return _plan_fallback(body)
    try:
        plan = await generate_plan_with_llm(
            provider,
            body.sports,
            body.gym_days,
            body.split_id,
            body.goal,
            body.catalog,
            system_prompt=body.system_prompt,
        )
    except LLMError:
        logger.exception("LLM plan generation failed (%s); using stub", provider.name)
        return _plan_fallback(body)
    if not any(
        day.day_type == "gimnasio" and day.exercises for day in plan.days
    ):
        logger.warning(
            "LLM plan has no gym content; falling back to stub (days=%d)",
            len(plan.days),
        )
        return _plan_fallback(body)
    return plan
