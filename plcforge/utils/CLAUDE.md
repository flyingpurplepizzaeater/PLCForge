# Utils Module

<!-- AUTO-MANAGED: module-description -->
Utility components for PLCForge, including real-time trend logging for PLC data with support for multiple export formats and historical data queries.
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: architecture -->
## Architecture

```
utils/
├── __init__.py              # Exports TrendLogger, TrendDataPoint, TrendConfig, TrendBuffer, ExportFormat
└── trend_logger.py          # Real-time data logging with CSV/JSON/SQLite export
```

**Trend Logger Components:**
- `TrendLogger` class for real-time PLC data collection
- `TrendBuffer` thread-safe circular buffer with `deque` and `threading.Lock`
- `TrendDataPoint` dataclass: timestamp, tag_name, value, quality
- `TrendConfig` dataclass: sample_interval_ms, max_points, auto_export, export_format, export_path, tags
- `ExportFormat` enum: CSV, JSON, SQLITE

**Data Collection:**
- Background thread for continuous sampling
- Configurable sampling interval (default 1000ms)
- Read callback function provided by user
- Optional data callback for real-time processing

**Storage:**
- In-memory circular buffer (default 10000 points)
- Optional SQLite persistence with indexed queries
- Automatic export when buffer full (if configured)
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: conventions -->
## Conventions

**Logger Usage:**
```python
logger = TrendLogger()
logger.configure(TrendConfig(
    sample_interval_ms=500,
    max_points=10000,
    tags=["Temperature", "Pressure", "Flow"]
))
logger.start(read_callback=plc.read_tag)
# ... logging runs in background ...
logger.stop()
logger.export_csv("trends.csv")
```

**Manual Logging:**
```python
logger = TrendLogger()
logger.log_value("TestTag", 42)
latest = logger.get_latest("TestTag")
points = logger.get_range_by_tag("TestTag", start_time, end_time)
```

**Buffer Operations:**
```python
buffer = TrendBuffer(max_size=10000)
buffer.append(TrendDataPoint(...))
points = buffer.get_all()
tag_points = buffer.get_by_tag("TagName")
range_points = buffer.get_range(start_time, end_time, tag_name)
buffer.clear()
```

**SQLite Schema:**
- Table: `trend_data`
- Columns: id (INTEGER PRIMARY KEY), timestamp (REAL), tag_name (TEXT), value (TEXT), quality (TEXT), created_at (TIMESTAMP)
- Indexes: `idx_trend_timestamp` on timestamp, `idx_trend_tag` on tag_name
- Thread-safe with `check_same_thread=False`

**Export Formats:**
- CSV: timestamp, datetime (ISO format), tag_name, value, quality
- JSON: Array of TrendDataPoint dictionaries with ISO datetime
- SQLite: Persistent database with indexed queries

**Thread Safety:**
- `TrendBuffer` uses `threading.Lock` for all operations
- Background sampling thread uses `threading.Thread`
- `_running` flag controls background thread lifecycle
- SQLite connection created with `check_same_thread=False`

**Data Quality:**
- Quality field: "Good", "Bad", "Uncertain"
- Default quality: "Good"
- Quality propagated from read callback or set manually

**Properties:**
- `TrendLogger.is_running`: Boolean indicating if background sampling active
- `TrendLogger.monitored_tags`: List of tags being monitored
- `TrendLogger.point_count`: Total points in buffer
- `TrendBuffer.size`: Current buffer size
- `TrendBuffer.is_full`: Boolean indicating buffer capacity
<!-- END AUTO-MANAGED -->

<!-- AUTO-MANAGED: dependencies -->
## Dependencies

- `csv` - CSV export (standard library)
- `json` - JSON export (standard library)
- `sqlite3` - Persistent storage (standard library)
- `threading` - Background sampling and thread safety (standard library)
- `time` - Timestamp generation (standard library)
- `datetime` - Datetime conversion and formatting (standard library)
- `pathlib.Path` - File path handling (standard library)
- `dataclasses` - Configuration and data point objects (standard library)
- `collections.deque` - Circular buffer implementation (standard library)
- `enum.Enum` - Export format enum (standard library)
<!-- END AUTO-MANAGED -->
