from fastapi import APIRouter, Depends

from app.api.schemas import CorrelationData, ValuesData
from app.core.deps import require_current_user
from app.services.analysis_service import category_parameters, correlation_parameters, number_parameters

router = APIRouter(
    prefix="/type-parameters",
    dependencies=[Depends(require_current_user)],
)


@router.post("/number")
async def number_params(data: ValuesData):
    return number_parameters(data.values)


@router.post("/category")
async def category_params(data: ValuesData):
    return category_parameters(data.values)


@router.post("/correlation")
async def correlation_matrix(data: CorrelationData):
    return correlation_parameters(data.data)
