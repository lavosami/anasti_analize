from typing import Any

from pydantic import BaseModel, Field


DatasetRow = dict[str, Any]
DatasetMap = dict[str, DatasetRow]
DatasetPayload = DatasetMap | list[DatasetRow]


class AnalysisData(BaseModel):
    data: DatasetPayload
    target: str | None = None


class GroupedData(BaseModel):
    data: DatasetPayload
    target: str


class NumberParams(BaseModel):
    mean: float
    median: float
    std: float
    min: float
    max: float


class CategoryParams(BaseModel):
    top_values: list[dict[str, Any]]
    unique_values: list[Any]


class ValuesData(BaseModel):
    values: list[Any]


class CorrelationData(BaseModel):
    data: DatasetPayload


class SummaryData(BaseModel):
    numeric: dict[str, NumberParams]
    categorical: dict[str, CategoryParams]
    correlation: dict[str, dict[str, float | None]]
    row_count: int = Field(ge=0)


class GroupAnalysis(BaseModel):
    rows: list[DatasetRow]
    summary: SummaryData


class AnalysisResponse(BaseModel):
    summary: SummaryData
    groups: dict[str, GroupAnalysis] | dict[str, dict[str, GroupAnalysis]] | None = None
