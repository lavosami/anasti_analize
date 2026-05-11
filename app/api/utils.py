from collections import Counter, defaultdict
from datetime import date, datetime
from math import isfinite, sqrt
import re
from typing import Any

from app.api.schemas import CategoryParams, GroupAnalysis, NumberParams, SummaryData

NUMBER_PATTERN = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")


def rows_from_data(data: Any) -> list[dict]:
    if isinstance(data, dict):
        rows = list(data.values())
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    return sort_rows_by_detected_date([row for row in rows if isinstance(row, dict)])


def sort_rows_by_detected_date(rows: list[dict]) -> list[dict]:
    date_field = find_date_sort_field(rows)
    if not date_field:
        return rows

    def sort_key(item: tuple[int, dict]) -> tuple[int, float, int]:
        index, row = item
        parsed = parse_datetime(row.get(date_field))
        if parsed is None:
            return (1, 0, index)
        return (0, parsed.timestamp(), index)

    return [row for _, row in sorted(enumerate(rows), key=sort_key)]


def find_date_sort_field(rows: list[dict]) -> str | None:
    columns: list[str] = []
    seen_columns: set[str] = set()

    for row in rows:
        for column in row:
            if column not in seen_columns:
                columns.append(column)
                seen_columns.add(column)

    selected_field: str | None = None
    selected_ratio = 0.0

    for column in columns:
        present_count = 0
        parsed_count = 0

        for row in rows:
            value = row.get(column)
            if value is None or value == "":
                continue
            present_count += 1
            if parse_datetime(value):
                parsed_count += 1

        ratio = parsed_count / present_count if present_count else 0
        if (
            present_count >= 2
            and parsed_count >= 2
            and ratio >= 0.6
            and ratio > selected_ratio
        ):
            selected_field = column
            selected_ratio = ratio

    return selected_field


def normalize_number_text(value: str) -> str:
    compact = "".join(value.split())
    if "," in compact and "." in compact:
        if compact.rfind(",") > compact.rfind("."):
            return compact.replace(".", "").replace(",", ".")
        return compact.replace(",", "")
    if "," in compact:
        return compact.replace(",", ".", 1)
    return compact


def parse_numeric_value(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        return numeric if isfinite(numeric) else None
    if isinstance(value, str):
        normalized = normalize_number_text(value.strip())
        if not normalized or not NUMBER_PATTERN.fullmatch(normalized):
            return None
        numeric = float(normalized)
        return numeric if isfinite(numeric) else None
    return None


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
            numeric_value = parse_numeric_value(value)
            if numeric_value is not None:
                numeric.setdefault(key, []).append(numeric_value)
            else:
                categorical.setdefault(key, []).append(value)

    return numeric, categorical


DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        normalized = raw.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return None


def infer_column_types(rows: list[dict]) -> dict[str, str]:
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "numeric": 0, "datetime": 0})

    for row in rows:
        for key, value in row.items():
            if value is None:
                continue
            stats[key]["total"] += 1
            if isinstance(value, bool):
                continue
            if parse_numeric_value(value) is not None:
                stats[key]["numeric"] += 1
                continue
            if parse_datetime(value):
                stats[key]["datetime"] += 1

    types: dict[str, str] = {}
    for key, counters in stats.items():
        total = counters["total"]
        if total == 0:
            continue
        if counters["datetime"] / total >= 0.6:
            types[key] = "datetime"
        elif counters["numeric"] / total >= 0.6:
            types[key] = "numeric"
        else:
            types[key] = "categorical"

    return types


def is_date_field(rows: list[dict], field: str) -> bool:
    parsed = 0
    total = 0
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        total += 1
        if parse_datetime(value):
            parsed += 1
    if total < 2:
        return False
    return parsed / total >= 0.6


def compute_number_params(values: list[Any]) -> NumberParams | None:
    cleaned = [
        numeric
        for v in values
        if (numeric := parse_numeric_value(v)) is not None
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


def compute_category_params(values: list[Any]) -> CategoryParams:
    cleaned = [v for v in values if v is not None]
    counts = Counter(cleaned)
    total_count = len(cleaned)

    top_values = [
        {
            "value": value,
            "count": count,
            "percentage": count / total_count * 100 if total_count else 0,
        }
        for value, count in counts.most_common()
    ]
    unique_values = list(counts.keys())

    return CategoryParams(
        top_values=top_values,
        unique_values=unique_values,
        total_count=total_count,
    )


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


def correlation_ratio(numeric_values: list[float], categories: list[Any]) -> float | None:
    if len(numeric_values) != len(categories):
        return None
    if len(numeric_values) < 2:
        return None

    overall_mean = sum(numeric_values) / len(numeric_values)
    totals: dict[Any, dict[str, float]] = defaultdict(lambda: {"count": 0, "sum": 0.0})

    for value, category in zip(numeric_values, categories, strict=True):
        totals[category]["count"] += 1
        totals[category]["sum"] += value

    ss_between = 0.0
    for stats in totals.values():
        if stats["count"] == 0:
            continue
        mean_k = stats["sum"] / stats["count"]
        ss_between += stats["count"] * (mean_k - overall_mean) ** 2

    ss_total = sum((value - overall_mean) ** 2 for value in numeric_values)
    if ss_total == 0:
        return 0.0

    return sqrt(ss_between / ss_total)


def cramers_v(values_a: list[Any], values_b: list[Any]) -> float | None:
    if len(values_a) != len(values_b):
        return None
    count = len(values_a)
    if count < 2:
        return None

    categories_a = sorted(set(values_a))
    categories_b = sorted(set(values_b))
    if len(categories_a) < 2 or len(categories_b) < 2:
        return 0.0

    index_a = {value: idx for idx, value in enumerate(categories_a)}
    index_b = {value: idx for idx, value in enumerate(categories_b)}

    table = [[0 for _ in categories_b] for _ in categories_a]
    for val_a, val_b in zip(values_a, values_b, strict=True):
        table[index_a[val_a]][index_b[val_b]] += 1

    row_totals = [sum(row) for row in table]
    col_totals = [sum(table[row][col] for row in range(len(categories_a))) for col in range(len(categories_b))]

    chi2 = 0.0
    for i, row in enumerate(table):
        for j, observed in enumerate(row):
            expected = (row_totals[i] * col_totals[j]) / count
            if expected > 0:
                chi2 += (observed - expected) ** 2 / expected

    phi2 = chi2 / count
    min_dim = min(len(categories_a) - 1, len(categories_b) - 1)
    if min_dim <= 0:
        return 0.0

    return sqrt(phi2 / min_dim)


def compute_correlation_matrix(rows: list[dict]) -> dict[str, dict[str, float | None]]:
    types = infer_column_types(rows)
    sorted_keys = sorted(types.keys())
    matrix: dict[str, dict[str, float | None]] = {key: {} for key in sorted_keys}

    for i, key_a in enumerate(sorted_keys):
        for key_b in sorted_keys[i:]:
            type_a = types[key_a]
            type_b = types[key_b]
            xs: list[float] = []
            ys: list[float] = []
            cats_a: list[Any] = []
            cats_b: list[Any] = []
            for row in rows:
                val_a = row.get(key_a)
                val_b = row.get(key_b)
                if val_a is None or val_b is None:
                    continue
                conv_a: float | str | None
                conv_b: float | str | None

                if type_a == "numeric":
                    conv_a = parse_numeric_value(val_a)
                elif type_a == "datetime":
                    parsed = parse_datetime(val_a)
                    conv_a = parsed.timestamp() if parsed else None
                else:
                    conv_a = str(val_a)

                if type_b == "numeric":
                    conv_b = parse_numeric_value(val_b)
                elif type_b == "datetime":
                    parsed = parse_datetime(val_b)
                    conv_b = parsed.timestamp() if parsed else None
                else:
                    conv_b = str(val_b)

                if conv_a is None or conv_b is None:
                    continue

                if type_a in ("numeric", "datetime"):
                    xs.append(float(conv_a))
                else:
                    cats_a.append(conv_a)

                if type_b in ("numeric", "datetime"):
                    ys.append(float(conv_b))
                else:
                    cats_b.append(conv_b)

            if type_a in ("numeric", "datetime") and type_b in ("numeric", "datetime"):
                corr = pearson_correlation(xs, ys)
            elif type_a == "categorical" and type_b == "categorical":
                corr = cramers_v(cats_a, cats_b)
            elif type_a == "categorical" and type_b in ("numeric", "datetime"):
                corr = correlation_ratio(ys, cats_a)
            elif type_b == "categorical" and type_a in ("numeric", "datetime"):
                corr = correlation_ratio(xs, cats_b)
            else:
                corr = None

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
