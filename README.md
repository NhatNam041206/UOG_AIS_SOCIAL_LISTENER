# 2020 Election Sentiment Analysis

A modular, object-oriented baseline for a 5-phase sentiment analysis pipeline over 2020 election-related data.

## Manual setup

1. Create and activate a virtual environment:
   - `python -m venv venv`
   - `source venv/bin/activate` (Linux/macOS) or `venv/Scripts/activate` (Windows)
2. Install dependencies:
   - `pip install -r requirements.txt`

## Phase 1 flexible ingestion

Stream readers are format adapters and do not define a fixed extraction schema.
Reader-specific pandas options and controller-owned transformation policy are supplied
when the ingestion service is executed:

```python
from src.phase1_ingestion.ingestion_runner_controller import IngestionRunnerController
from src.phase1_ingestion.stream_readers_model import CsvStreamReader

controller = IngestionRunnerController(CsvStreamReader())
dataframe = controller.run(
    "data/01_raw/tweets.csv",
    {
        "reader_options": {"encoding": "utf-8"},
        "fields": ["id", "date", "tweet", "user_loc"],
        "timestamp_columns": "date",
    },
)
```

Supported controller options:

- `reader_options`: forwarded to the configured pandas CSV or JSON reader.
- `fields`: optional output projection applied after schema mapping.
- `timestamp_columns`: optional column name or sequence of columns converted to UTC.
- `timestamp_errors`: timestamp conversion behavior, either `raise` or `coerce`.

A schema mapper can be injected into `IngestionRunnerController` when a source needs
field renaming or structural transformation. Without one, the controller operates on
the source columns directly.
