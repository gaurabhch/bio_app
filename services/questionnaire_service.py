"""
Questionnaire service — submit and retrieve PCOS risk assessments.
Ported from questionnair_app/app/services/questionnaire_service.py.
"""

from uuid import uuid4
import json

from schemas.questionnaire import (
    QuestionnaireSubmitRequest,
    AssessmentSubmitResponse,
)
from services.pcos_scoring_engine import PCOSScoringEngine
from core.database import get_async_pool


class QuestionnaireService:
    def __init__(self):
        self.scoring_engine = PCOSScoringEngine()

    async def submit(self, req: QuestionnaireSubmitRequest, user_id: str) -> AssessmentSubmitResponse:
        from uuid import UUID
        result = self.scoring_engine.score(req)
        assessment_id = uuid4()

        # Parse user_id string to UUID object
        parsed_user_id = UUID(user_id) if user_id else None

        req_payload = req.model_dump(mode="json")
        result_payload = result.model_dump(mode="json")

        pool = await get_async_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO pcos_assessments (
                    id,
                    user_id,
                    input_data,
                    result_data,
                    risk_tier,
                    composite_score
                )
                VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6)
                """,
                assessment_id,
                parsed_user_id,
                json.dumps(req_payload),
                json.dumps(result_payload),
                result.risk_tier,
                result.composite_score,
            )

        return AssessmentSubmitResponse(
            assessment_id=str(assessment_id),
            **result_payload
        )

    async def get_results(self, assessment_id: str):
        pool = await get_async_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, result_data
                FROM pcos_assessments
                WHERE id = $1::uuid
                """,
                assessment_id,
            )

        if not row:
            return None

        result_payload = dict(row["result_data"])

        return AssessmentSubmitResponse(
            assessment_id=str(row["id"]),
            **result_payload
        )

    async def get_user_history(self, user_id: str):
        from uuid import UUID
        try:
            parsed_user_id = UUID(user_id)
        except ValueError:
            return []

        pool = await get_async_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, result_data, created_at
                FROM pcos_assessments
                WHERE user_id = $1::uuid
                ORDER BY created_at DESC
                """,
                parsed_user_id,
            )

        return [
            {
                "assessment_id": str(row["id"]),
                "created_at": str(row["created_at"]),
                **dict(row["result_data"])
            }
            for row in rows
        ]
