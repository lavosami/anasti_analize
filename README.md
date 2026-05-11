# anasti_analize

Service for dataset analysis in the Anasti project.

## Run

```bash
uvicorn main:app --reload
```

Set `JWT_SECRET` to the same value used by the `auth` service. Protected endpoints also support `JWT_ALGORITHM` and default it to `HS256`.

## Auth

All non-root endpoints require `Authorization: Bearer <access-token>`.

This service does not persist datasets. It only processes the request payload in memory.

## API

### `POST /analysis`

Builds a dataset summary. If `target` is passed, the response also contains grouped rows and a separate summary for each group.

Request:

```json
{
  "data": {
    "1": {"age": 21, "salary": 1000, "city": "Moscow", "segment": "A"},
    "2": {"age": 25, "salary": 1200, "city": "SPB", "segment": "B"},
    "3": {"age": 23, "salary": 1100, "city": "Moscow", "segment": "A"}
  },
  "target": "segment"
}
```

Response:

```json
{
  "summary": {
    "numeric": {
      "age": {"mean": 23.0, "median": 23.0, "std": 1.632993161855452, "min": 21.0, "max": 25.0},
      "salary": {"mean": 1100.0, "median": 1100.0, "std": 81.64965809277261, "min": 1000.0, "max": 1200.0}
    },
    "categorical": {
      "city": {
        "top_values": [
          {"value": "Moscow", "count": 2, "percentage": 66.66666666666666},
          {"value": "SPB", "count": 1, "percentage": 33.33333333333333}
        ],
        "unique_values": ["Moscow", "SPB"],
        "total_count": 3
      },
      "segment": {
        "top_values": [
          {"value": "A", "count": 2, "percentage": 66.66666666666666},
          {"value": "B", "count": 1, "percentage": 33.33333333333333}
        ],
        "unique_values": ["A", "B"],
        "total_count": 3
      }
    },
    "correlation": {
      "age": {"age": 1.0, "salary": 1.0},
      "salary": {"age": 1.0, "salary": 1.0}
    },
    "row_count": 3
  },
  "groups": {
    "A": {
      "rows": [
        {"age": 21, "salary": 1000, "city": "Moscow", "segment": "A"},
        {"age": 23, "salary": 1100, "city": "Moscow", "segment": "A"}
      ],
      "summary": {
        "numeric": {
          "age": {"mean": 22.0, "median": 22.0, "std": 1.0, "min": 21.0, "max": 23.0},
          "salary": {"mean": 1050.0, "median": 1050.0, "std": 50.0, "min": 1000.0, "max": 1100.0}
        },
        "categorical": {
          "city": {
            "top_values": [{"value": "Moscow", "count": 2, "percentage": 100.0}],
            "unique_values": ["Moscow"],
            "total_count": 2
          },
          "segment": {
            "top_values": [{"value": "A", "count": 2, "percentage": 100.0}],
            "unique_values": ["A"],
            "total_count": 2
          }
        },
        "correlation": {
          "age": {"age": 1.0, "salary": 1.0},
          "salary": {"age": 1.0, "salary": 1.0}
        },
        "row_count": 2
      }
    },
    "B": {
      "rows": [
        {"age": 25, "salary": 1200, "city": "SPB", "segment": "B"}
      ],
      "summary": {
        "numeric": {
          "age": {"mean": 25.0, "median": 25.0, "std": 0.0, "min": 25.0, "max": 25.0},
          "salary": {"mean": 1200.0, "median": 1200.0, "std": 0.0, "min": 1200.0, "max": 1200.0}
        },
        "categorical": {
          "city": {
            "top_values": [{"value": "SPB", "count": 1, "percentage": 100.0}],
            "unique_values": ["SPB"],
            "total_count": 1
          },
          "segment": {
            "top_values": [{"value": "B", "count": 1, "percentage": 100.0}],
            "unique_values": ["B"],
            "total_count": 1
          }
        },
        "correlation": {
          "age": {"age": null, "salary": null},
          "salary": {"age": null, "salary": null}
        },
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
    {"city": "Moscow", "segment": "A"},
    {"city": "SPB", "segment": "B"},
    {"city": "Moscow", "segment": "A"}
  ],
  "target": "segment"
}
```

Response:

```json
{
  "A": [
    {"city": "Moscow", "segment": "A"},
    {"city": "Moscow", "segment": "A"}
  ],
  "B": [
    {"city": "SPB", "segment": "B"}
  ]
}
```

### `POST /type-parameters/number`

Request:

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

### `POST /type-parameters/category`

Request:

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
      {"value": "A", "count": 2, "percentage": 50.0},
      {"value": "B", "count": 1, "percentage": 25.0},
      {"value": "C", "count": 1, "percentage": 25.0}
    ],
    "unique_values": ["A", "B", "C"],
    "total_count": 4
  }
}
```

### `POST /type-parameters/correlation`

Request:

```json
{
  "data": [
    {"age": 21, "salary": 1000, "score": 70},
    {"age": 25, "salary": 1200, "score": 80},
    {"age": 23, "salary": 1100, "score": 75}
  ]
}
```

Response:

```json
{
  "matrix": {
    "age": {"age": 1.0, "salary": 1.0, "score": 1.0},
    "salary": {"age": 1.0, "salary": 1.0, "score": 1.0},
    "score": {"age": 1.0, "salary": 1.0, "score": 1.0}
  }
}
```
