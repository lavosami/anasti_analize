from typing import Any

from app.api.schemas import AnalysisData, AnalysisResponse, GroupAnalysis, GroupedData
from app.api.utils import (
    build_group_analyses,
    compute_category_params,
    compute_correlation_matrix,
    compute_number_params,
    is_date_field,
    parse_datetime,
    rows_from_data,
    summarize_dataset,
)


def build_analysis(data: AnalysisData | dict[str, Any]) -> dict[str, Any]:
    payload = data if isinstance(data, AnalysisData) else AnalysisData(**data)
    summary = summarize_dataset(payload.data)
    response = AnalysisResponse(summary=summary)

    if payload.target:
        groups = group_rows({"data": payload.data, "target": payload.target})
        response.groups = build_group_analyses_nested(groups)

    return response.model_dump(mode="json")


def group_rows(data: GroupedData | dict[str, Any]) -> dict[str, list[dict]] | dict[str, dict[str, list[dict]]]:
    payload = data if isinstance(data, GroupedData) else GroupedData(**data)
    rows = rows_from_data(payload.data)
    if is_date_field(rows, payload.target):
        return group_rows_by_date(rows, payload.target)

    groups: dict[str, list[dict]] = {}

    for row in rows:
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


def build_group_analyses_nested(
    groups: dict[str, list[dict]] | dict[str, dict[str, list[dict]]],
) -> dict[str, GroupAnalysis] | dict[str, dict[str, GroupAnalysis]]:
    sample = next(iter(groups.values()), None)
    if isinstance(sample, list):
        return build_group_analyses(groups)  # type: ignore[arg-type]

    grouped: dict[str, dict[str, GroupAnalysis]] = {}
    for bucket, bucket_groups in groups.items():
        grouped[bucket] = build_group_analyses(bucket_groups)
    return grouped


def group_rows_by_date(rows: list[dict], field: str) -> dict[str, dict[str, list[dict]]]:
    time_groups: dict[str, list[dict]] = {}
    weekday_groups: dict[str, list[dict]] = {}
    month_day_groups: dict[str, list[dict]] = {}
    month_groups: dict[str, list[dict]] = {}
    quarter_groups: dict[str, list[dict]] = {}
    year_groups: dict[str, list[dict]] = {}

    for row in rows:
        raw = row.get(field)
        parsed = parse_datetime(raw)
        if not parsed:
            continue

        time_key = f"{parsed.hour:02d}:{parsed.minute:02d}"
        weekday_key = str(parsed.weekday())
        month_day_key = str(parsed.day)
        month_key = str(parsed.month)
        quarter_key = str(((parsed.month - 1) // 3) + 1)
        year_key = str(parsed.year)

        time_groups.setdefault(time_key, []).append(row)
        weekday_groups.setdefault(weekday_key, []).append(row)
        month_day_groups.setdefault(month_day_key, []).append(row)
        month_groups.setdefault(month_key, []).append(row)
        quarter_groups.setdefault(quarter_key, []).append(row)
        year_groups.setdefault(year_key, []).append(row)

    buckets = {
        "time": time_groups,
        "weekday": weekday_groups,
        "month_day": month_day_groups,
        "month": month_groups,
        "quarter": quarter_groups,
        "year": year_groups,
    }

    return {bucket: groups for bucket, groups in buckets.items() if len(groups) > 1}
