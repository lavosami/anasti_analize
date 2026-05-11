# Anasti Analize Service

FastAPI service and RabbitMQ RPC worker for dataset analysis in Anasti.

The service accepts list-based or map-based dataset payloads, computes summaries, and can group rows by a target field. It processes request data in memory and does not persist datasets or results.

## Capabilities

- Numeric summaries: mean, median, standard deviation, minimum, and maximum.
- Categorical summaries: top values, unique values, counts, and percentages.
- Correlation matrices for numeric, datetime, and categorical fields.
- Target grouping with a summary for each group.
- Date-aware grouping by time, weekday, day of month, month, quarter, and year when the target field looks like a date.
- Automatic row sorting by a detected date-like column.

## Requirements

- Python 3.14+
- RabbitMQ. The service starts its RPC consumer on application startup.

Docker Compose provides RabbitMQ and environment defaults for local development.

## Installation

Using `uv`:

```bash
uv sync
```

Using `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set these environment variables when running outside Docker Compose:

- `JWT_SECRET`: secret used to validate access tokens on direct HTTP routes.
- `JWT_ALGORITHM`: signing algorithm. Defaults to `HS256`.
- `AMQP_URL`: RabbitMQ URL. Defaults to `amqp://guest:guest@rabbitmq:5672/`.
- `ANALYSIS_RPC_QUEUE`: RPC queue name. Defaults to `analysis.rpc`.

`JWT_SECRET` and `JWT_ALGORITHM` must match the auth service.

## Running

With Docker Compose from the repository root:

```bash
docker compose up --build rabbitmq anasti_analize
```

Run locally from this directory:

```bash
export AMQP_URL=amqp://guest:guest@localhost:5672/
export JWT_SECRET=super-secret-jwt-key
uvicorn main:app --reload
```

or:

```bash
AMQP_URL=amqp://guest:guest@localhost:5672/ JWT_SECRET=super-secret-jwt-key \
fastapi dev main.py
```

Open:

- Root endpoint: `http://127.0.0.1:8000/`
- Interactive docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

When started through Docker Compose, the service is published at `http://localhost:8003`.

## Auth

All direct HTTP endpoints except `/` require:

```http
Authorization: Bearer <access-token>
```

The API gateway validates the same access token before forwarding work through RabbitMQ.

## Dataset Shape

The service accepts either a list of rows:

```json
{
  "data": [
    { "age": 21, "salary": 1000, "city": "Moscow", "segment": "A" },
    { "age": 25, "salary": 1200, "city": "SPB", "segment": "B" }
  ]
}
```

or a map of row ids to rows:

```json
{
  "data": {
    "1": { "age": 21, "salary": 1000, "city": "Moscow", "segment": "A" },
    "2": { "age": 25, "salary": 1200, "city": "SPB", "segment": "B" }
  }
}
```

The frontend sends the map form after importing column-oriented data from the collector.

## HTTP API

Direct analysis routes are mounted at the service root.

When called through the API gateway, prefix the same analysis paths with `/analysis`:

```text
Direct service: /analysis
Gateway:        /analysis/analysis
```

### `POST /analysis`

Builds a dataset summary. If `target` is provided, the response also includes grouped rows and group summaries.

Request:

```json
{
  "data": {
    "1": { "age": 21, "salary": 1000, "city": "Moscow", "segment": "A" },
    "2": { "age": 25, "salary": 1200, "city": "SPB", "segment": "B" },
    "3": { "age": 23, "salary": 1100, "city": "Moscow", "segment": "A" }
  },
  "target": "segment"
}
```

Response shape:

```json
{
  "summary": {
    "numeric": {
      "age": {
        "mean": 23.0,
        "median": 23.0,
        "std": 1.632993161855452,
        "min": 21.0,
        "max": 25.0
      }
    },
    "categorical": {
      "city": {
        "top_values": [
          { "value": "Moscow", "count": 2, "percentage": 66.66666666666666 }
        ],
        "unique_values": ["Moscow", "SPB"],
        "total_count": 3
      }
    },
    "correlation": {
      "age": { "age": 1.0, "salary": 1.0 }
    },
    "row_count": 3
  },
  "groups": {
    "A": {
      "rows": [{ "age": 21, "salary": 1000, "city": "Moscow", "segment": "A" }],
      "summary": {
        "numeric": {},
        "categorical": {},
        "correlation": {},
        "row_count": 1
      }
    }
  }
}
```

### `POST /get-groups`

Groups dataset rows by the `target` field.

Request:

```json
{
  "data": [
    { "city": "Moscow", "segment": "A" },
    { "city": "SPB", "segment": "B" },
    { "city": "Moscow", "segment": "A" }
  ],
  "target": "segment"
}
```

Response:

```json
{
  "A": [
    { "city": "Moscow", "segment": "A" },
    { "city": "Moscow", "segment": "A" }
  ],
  "B": [{ "city": "SPB", "segment": "B" }]
}
```

When the target is date-like, groups are nested by buckets such as `time`, `weekday`, `month_day`, `month`, `quarter`, and `year`.

### `POST /type-parameters/number`

Computes numeric parameters from a list of values.

```json
{
  "values": [1, 2, 3, 4, 5]
}
```

Response:

```json
{
  "params": {
    "mean": 3.0,
    "median": 3.0,
    "std": 1.4142135623730951,
    "min": 1.0,
    "max": 5.0
  }
}
```

Returns `{"params": null}` when no numeric values can be parsed.

### `POST /type-parameters/category`

Computes categorical parameters from a list of values.

```json
{
  "values": ["A", "B", "A", "C"]
}
```

Response:

```json
{
  "params": {
    "top_values": [
      { "value": "A", "count": 2, "percentage": 50.0 },
      { "value": "B", "count": 1, "percentage": 25.0 }
    ],
    "unique_values": ["A", "B", "C"],
    "total_count": 4
  }
}
```

### `POST /type-parameters/correlation`

Builds a correlation matrix for all detected fields.

```json
{
  "data": [
    { "age": 21, "salary": 1000, "score": 70 },
    { "age": 25, "salary": 1200, "score": 80 },
    { "age": 23, "salary": 1100, "score": 75 }
  ]
}
```

Response:

```json
{
  "matrix": {
    "age": { "age": 1.0, "salary": 1.0, "score": 1.0 },
    "salary": { "age": 1.0, "salary": 1.0, "score": 1.0 },
    "score": { "age": 1.0, "salary": 1.0, "score": 1.0 }
  }
}
```

## RabbitMQ RPC

On startup, the service connects to `AMQP_URL`, declares `ANALYSIS_RPC_QUEUE`, and consumes JSON RPC messages from the API gateway.

Supported RPC actions:

- `analysis`
- `get_groups`
- `number_params`
- `category_params`
- `correlation_params`

Successful RPC responses use:

```json
{
  "status": "ok",
  "data": {
    "summary": {
      "numeric": {},
      "categorical": {},
      "correlation": {},
      "row_count": 0
    }
  }
}
```

Errors use:

```json
{
  "status": "error",
  "error": {
    "status_code": 400,
    "detail": "Unsupported analysis action"
  }
}
```

## Project Structure

```text
app/
  api/
    routes/              # Direct HTTP analysis endpoints
    schemas.py           # Request and response models
    utils.py             # Statistics, grouping, parsing, correlations
  core/
    config.py            # JWT settings
    deps.py              # Bearer-token dependency
    security.py          # Access-token decoding
  messaging/
    rpc.py               # RabbitMQ analysis RPC server
  services/
    analysis_service.py  # Application-level analysis functions
main.py                  # FastAPI app and RPC lifespan
```

## Notes

- Numeric parsing accepts numbers and numeric strings, including comma decimal separators.
- Boolean values are treated as categorical values.
- Datetime-like fields are recognized from common ISO and day/month formats.
- Correlations use Pearson for numeric/datetime pairs, Cramer's V for categorical pairs, and correlation ratio for mixed categorical/numeric pairs.
