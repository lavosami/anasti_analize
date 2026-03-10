from fastapi import APIRouter, Depends

from app.api.schemas import AnalysisData, AnalysisResponse, GroupedData
from app.api.utils import build_group_analyses, rows_from_data, summarize_dataset
from app.core.deps import require_current_user

router = APIRouter(dependencies=[Depends(require_current_user)])


@router.post("/analysis", response_model=AnalysisResponse)
async def analysis(data: AnalysisData) -> AnalysisResponse:
    """
    Analysis of user's dataset

    :param data: user's dataset (with or without target variable)
    :return: dict of analysis results
    """

    summary = summarize_dataset(data.data)
    response = AnalysisResponse(summary=summary)

    if data.target:
        groups = await get_groups(GroupedData(data=data.data, target=data.target))
        response.groups = build_group_analyses(groups)

    return response


@router.post("/get-groups")
async def get_groups(data: GroupedData) -> dict[str, list[dict]]:
    """
    Get groups by target variable

    :param data: user's dataset with target variable
    :return: grouped by target variable dataset
    """
    groups: dict[str, list[dict]] = {}
    for row in rows_from_data(data.data):
        target_value = row.get(data.target)
        if target_value is None:
            continue
        group_key = str(target_value)
        try:
            groups[group_key].append(row)
        except KeyError:
            groups[group_key] = [row]

    return groups
