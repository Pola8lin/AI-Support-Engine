from fastapi import APIRouter, HTTPException

from src.models.response import AnalyzeRequest, AnalyzeResponse
from src.services.analyzer import AnalyzerService


router = APIRouter()
analyzer = AnalyzerService()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_message(request: AnalyzeRequest):
    try:
        return analyzer.analyze(request)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error)
        )
    