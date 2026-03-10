from collections import Counter
from math import isfinite, sqrt
from typing import Any

from app.api.schemas import CategoryParams, GroupAnalysis, NumberParams, SummaryData


def rows_from_data(data: Any) -> list[dict]:
    if isinstance(data, dict):
        rows = list(data.values())
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    return [row for row in rows if isinstance(row, dict)]


def split_columns(rows: list[dict]) -> tuple[dict[str, list[float]], dict[str, list[Any]]]:
    numeric: dict[str, list[float]] = {}
    categorical: dict[str, list[Any]] = {}

    for row in rows:
        for key, value in row.items():
            if value is None:
                continue
            if isinstance(value, bool):
                categorical.setdefault(key, []).append(value)
                continue
            if isinstance(value, (int, float)) and isfinite(float(value)):
                numeric.setdefault(key, []).append(float(value))
            else:
                categorical.setdefault(key, []).append(value)

    return numeric, categorical


def compute_number_params(values: list[Any]) -> NumberParams | None:
    cleaned = [
        float(v)
        for v in values
        if isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(float(v))
    ]
    if not cleaned:
        return None

    cleaned.sort()
    count = len(cleaned)
    mean = sum(cleaned) / count

    mid = count // 2
    if count % 2 == 0:
        median = (cleaned[mid - 1] + cleaned[mid]) / 2
    else:
        median = cleaned[mid]

    variance = sum((v - mean) ** 2 for v in cleaned) / count
    std = sqrt(variance)

    return NumberParams(
        mean=mean,
        median=median,
        std=std,
        min=cleaned[0],
        max=cleaned[-1],
    )


def compute_category_params(values: list[Any], top_n: int = 5) -> CategoryParams:
    cleaned = [v for v in values if v is not None]
    counts = Counter(cleaned)

    top_values = [
        {"value": value, "count": count} for value, count in counts.most_common(top_n)
    ]
    unique_values = list(counts.keys())

    return CategoryParams(top_values=top_values, unique_values=unique_values)


def pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys):
        return None
    count = len(xs)
    if count < 2:
        return None

    mean_x = sum(xs) / count
    mean_y = sum(ys) / count

    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den_x = sum((x - mean_x) ** 2 for x in xs)
    den_y = sum((y - mean_y) ** 2 for y in ys)
    denom = sqrt(den_x * den_y)

    if denom == 0:
        return 0.0

    return num / denom


def compute_correlation_matrix(rows: list[dict]) -> dict[str, dict[str, float | None]]:
    keys: set[str] = set()

    for row in rows:
        for key, value in row.items():
            if isinstance(value, bool) or value is None:
                continue
            if isinstance(value, (int, float)) and isfinite(float(value)):
                keys.add(key)

    sorted_keys = sorted(keys)
    matrix: dict[str, dict[str, float | None]] = {key: {} for key in sorted_keys}

    for i, key_a in enumerate(sorted_keys):
        for key_b in sorted_keys[i:]:
            xs: list[float] = []
            ys: list[float] = []
            for row in rows:
                val_a = row.get(key_a)
                val_b = row.get(key_b)
                if (
                        isinstance(val_a, (int, float))
                        and not isinstance(val_a, bool)
                        and isfinite(float(val_a))
                        and isinstance(val_b, (int, float))
                        and not isinstance(val_b, bool)
                        and isfinite(float(val_b))
                ):
                    xs.append(float(val_a))
                    ys.append(float(val_b))

            corr = pearson_correlation(xs, ys)
            matrix[key_a][key_b] = corr
            matrix[key_b][key_a] = corr

    return matrix


def summarize_dataset(data: Any) -> SummaryData:
    rows = rows_from_data(data)
    numeric, categorical = split_columns(rows)

    numeric_summary = {
        key: compute_number_params(values)
        for key, values in numeric.items()
        if values
    }

    categorical_summary = {
        key: compute_category_params(values)
        for key, values in categorical.items()
        if values
    }

    correlation = compute_correlation_matrix(rows)

    return SummaryData(
        numeric=numeric_summary,
        categorical=categorical_summary,
        correlation=correlation,
        row_count=len(rows),
    )


def build_group_analyses(groups: dict[str, list[dict]]) -> dict[str, GroupAnalysis]:
    return {
        group_name: GroupAnalysis(
            rows=rows,
            summary=summarize_dataset(rows),
        )
        for group_name, rows in groups.items()
    }
