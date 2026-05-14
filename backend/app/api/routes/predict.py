"""
API endpoint for ML-based is_a_buyer prediction.

POST /api/v1/predict
  Body: {"review_text": "..."}
  Returns: prediction result with confidence and per-model probabilities.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ml_service import predict

router = APIRouter(prefix="/predict", tags=["predict"])


class PredictRequest(BaseModel):
    review_text: str = Field(min_length=1, max_length=5000)


class ModelProbabilities(BaseModel):
    bow_rf: float
    bow_lr: float
    ft_lr: float


class PredictResponse(BaseModel):
    predicted_is_buyer: bool
    confidence: float
    model_probabilities: ModelProbabilities
    fusion_method: str


@router.post("/", response_model=PredictResponse)
def predict_buyer(request: PredictRequest) -> PredictResponse:
    """
    Predict whether a reviewer is a buyer based on their review text.

    Uses 3 fused models (soft voting):
    - BoW + Random Forest
    - BoW + Logistic Regression
    - FastText + Logistic Regression
    """
    result = predict(request.review_text)
    return PredictResponse(
        predicted_is_buyer=result["predicted_is_buyer"],
        confidence=result["confidence"],
        model_probabilities=ModelProbabilities(**result["model_probabilities"]),
        fusion_method=result["fusion_method"],
    )
