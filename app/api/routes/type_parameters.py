from fastapi import APIRouter

from app.api.schemas import CorrelationData, ValuesData
from app.api.utils import compute_category_params, compute_correlation_matrix, compute_number_params, rows_from_data

router = APIRouter(prefix="/type-parameters")


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
