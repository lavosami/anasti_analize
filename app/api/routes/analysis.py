from fastapi import APIRouter, Depends

from app.api.schemas import AnalysisData, AnalysisResponse, GroupedData
from app.core.deps import require_current_user
from app.services.analysis_service import build_analysis, group_rows

router = APIRouter(dependencies=[Depends(require_current_user)])


@router.post("/analysis", response_model=AnalysisResponse)
async def analysis(data: AnalysisData) -> AnalysisResponse:
    """
    Analysis of user's dataset

    :param data: user's dataset (with or without target variable)
    :return: dict of analysis results
    """
    return AnalysisResponse(**build_analysis(data))


@router.post("/get-groups")
async def get_groups(data: GroupedData) -> dict[str, list[dict]]:
    """
    Get groups by target variable

    :param data: user's dataset with target variable
    :return: grouped by target variable dataset
    """
    return group_rows(data)
