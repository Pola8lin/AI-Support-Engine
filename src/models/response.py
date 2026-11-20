from enum import Enum
from pydantic import BaseModel, Field


class Category(str, Enum):
    ACCESS = "ACCESS"
    BUG = "BUG"
    FEATURE = "FEATURE"
    SECURITY = "SECURITY"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnalysisMode(str, Enum):
    TRADITIONAL = "traditional"
    GENERATIVE = "generative"


class AnalyzeRequest(BaseModel):
    message: str = Field(
        min_length=1,
        description="Mensaje o solicitud del usuario"
    )
    mode: AnalysisMode = AnalysisMode.TRADITIONAL


class AnalyzeResponse(BaseModel):
    category: Category
    priority: Priority
    response: str
    requiresHumanReview: bool
    mode: AnalysisMode
