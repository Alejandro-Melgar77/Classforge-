from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


class VerdictType(str, Enum):
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    INFORMACION_INSUFICIENTE = "INFORMACION_INSUFICIENTE"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecommendationPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RubricCriterionDefinition(BaseModel):
    code: str
    name: str
    weight: float
    description: str
    min_passing_score: float = 40.0
    evaluation_hints: List[str] = Field(default_factory=list)


class RubricDefinition(BaseModel):
    code: str
    version: str
    name: str
    description: str
    passing_score: float = 70.0
    criteria: List[RubricCriterionDefinition]
