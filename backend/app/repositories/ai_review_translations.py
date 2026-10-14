import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CopilotConclusion, CopilotReviewTranslation
from app.services.ai_review_translation import (
    AI_REVIEW_TRANSLATION_PROMPT_VERSION,
    AI_REVIEW_TRANSLATION_SCHEMA_VERSION,
)
from app.services.llm_copilot import AiReviewStructuredResult


class AiReviewTranslationRepository:
    def __init__(self, session: Session):
        self.session = session

    def find(
        self, conclusion_id: int, locale: str
    ) -> CopilotReviewTranslation | None:
        return self.session.scalar(
            select(CopilotReviewTranslation).where(
                CopilotReviewTranslation.conclusion_id == conclusion_id,
                CopilotReviewTranslation.locale == locale,
            )
        )

    def create(
        self,
        conclusion: CopilotConclusion,
        locale: str,
        translated: AiReviewStructuredResult,
        provider_model: str | None,
    ) -> CopilotReviewTranslation:
        record = CopilotReviewTranslation(
            conclusion_id=conclusion.id,
            locale=locale,
            translation_json=json.dumps(
                translated.model_dump(mode="json"), ensure_ascii=False
            ),
            prompt_version=AI_REVIEW_TRANSLATION_PROMPT_VERSION,
            schema_version=AI_REVIEW_TRANSLATION_SCHEMA_VERSION,
            provider_model=provider_model,
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record
