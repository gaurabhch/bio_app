"""
Questionnaire routes — PCOS risk assessment submission and retrieval.
Ported from questionnair_app/main.py.
"""

from fastapi import APIRouter, HTTPException

from schemas.questionnaire import QuestionnaireSubmitRequest, AssessmentSubmitResponse
from services.questionnaire_service import QuestionnaireService
from core.database import get_async_pool

router = APIRouter(prefix="/questionnaire", tags=["Questionnaire"])

service = QuestionnaireService()


@router.post("/submit", response_model=AssessmentSubmitResponse)
async def submit_questionnaire(req: QuestionnaireSubmitRequest, user_id: str):
    try:
        return await service.submit(req, user_id)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/results/{assessment_id}", response_model=AssessmentSubmitResponse)
async def get_results(assessment_id: str):
    try:
        result = await service.get_results(assessment_id)
        if not result:
            raise HTTPException(status_code=404, detail="Assessment not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/history/{user_id}")
async def get_user_history(user_id: str):
    try:
        return await service.get_user_history(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
