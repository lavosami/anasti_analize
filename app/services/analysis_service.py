from typing import Any

from app.api.schemas import AnalysisData, AnalysisResponse, GroupedData
from app.api.utils import build_group_analyses, compute_category_params, compute_correlation_matrix, compute_number_params, rows_from_data, summarize_dataset


def build_analysis(data: AnalysisData | dict[str, Any]) -> dict[str, Any]:
    payload = data if isinstance(data, AnalysisData) else AnalysisData(**data)
    summary = summarize_dataset(payload.data)
    response = AnalysisResponse(summary=summary)

    if payload.target:
        groups = group_rows({"data": payload.data, "target": payload.target})
        response.groups = build_group_analyses(groups)

    return response.model_dump(mode="json")


def group_rows(data: GroupedData | dict[str, Any]) -> dict[str, list[dict]]:
    payload = data if isinstance(data, GroupedData) else GroupedData(**data)
    groups: dict[str, list[dict]] = {}

    for row in rows_from_data(payload.data):
        target_value = row.get(payload.target)
        if target_value is None:
            continue
        group_key = str(target_value)
        groups.setdefault(group_key, []).append(row)

    return groups


def number_parameters(values: list[Any]) -> dict[str, Any]:
    params = compute_number_params(values)
    return {"params": params.model_dump(mode="json") if params is not None else None}


def category_parameters(values: list[Any]) -> dict[str, Any]:
    params = compute_category_params(values)
    return {"params": params.model_dump(mode="json")}


def correlation_parameters(data: Any) -> dict[str, Any]:
    rows = rows_from_data(data)
    matrix = compute_correlation_matrix(rows)
    return {"matrix": matrix}
