from fastapi import APIRouter, Depends

from app.api.schemas import CorrelationData, ValuesData
from app.api.utils import compute_category_params, compute_correlation_matrix, compute_number_params, rows_from_data
from app.core.deps import require_current_user

router = APIRouter(
    prefix="/type-parameters",
    dependencies=[Depends(require_current_user)],
)


@router.post("/number")
async def number_params(data: ValuesData):
    params = compute_number_params(data.values)
    return {"params": params}


@router.post("/category")
async def category_params(data: ValuesData):
    params = compute_category_params(data.values)
    return {"params": params}


@router.post("/correlation")
async def correlation_matrix(data: CorrelationData):
    rows = rows_from_data(data.data)
    matrix = compute_correlation_matrix(rows)
    return {"matrix": matrix}
