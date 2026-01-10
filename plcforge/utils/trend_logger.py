"""
Real-Time Trend Logger for PLC Data

Provides data logging and trending capabilities for monitoring PLC tag values
over time with support for:
- Real-time data collection
- CSV/JSON export
- Historical data queries
- Configurable sampling rates
- Rolling buffer storage
"""

import csv
import json
import sqlite3
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ExportFormat(Enum):
    """Supported export formats"""
    CSV = "csv"
    JSON = "json"
    SQLITE = "sqlite"


@dataclass
class TrendDataPoint:
    """Single data point in a trend"""
    timestamp: float  # Unix timestamp
    tag_name: str
    value: Any
    quality: str = "Good"  # Good, Bad, Uncertain

    @property
    def datetime(self) -> datetime:
        """Get timestamp as datetime object"""
        return datetime.fromtimestamp(self.timestamp)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp,
            "datetime": self.datetime.isoformat(),
            "tag_name": self.tag_name,
            "value": self.value,
            "quality": self.quality,
        }


@dataclass
class TrendConfig:
    """Configuration for trend logging"""
    sample_interval_ms: int = 1000  # Sampling interval in milliseconds
    max_points: int = 10000  # Maximum points to keep in memory
    auto_export: bool = False  # Automatically export when buffer full
    export_format: ExportFormat = ExportFormat.CSV
    export_path: Path | None = None
    tags: list[str] = field(default_factory=list)  # Tags to monitor


class TrendBuffer:
    """Thread-safe circular buffer for trend data"""

    def __init__(self, max_size: int = 10000):
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._max_size = max_size

    def append(self, point: TrendDataPoint) -> None:
        """Add data point to buffer"""
        with self._lock:
            self._buffer.append(point)

    def get_all(self) -> list[TrendDataPoint]:
        """Get all points in buffer"""
        with self._lock:
            return list(self._buffer)

    def get_by_tag(self, tag_name: str) -> list[TrendDataPoint]:
        """Get all points for a specific tag"""
        with self._lock:
            return [p for p in self._buffer if p.tag_name == tag_name]

    def get_range(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        tag_name: str | None = None
    ) -> list[TrendDataPoint]:
        """Get points within time range"""
        with self._lock:
            points = list(self._buffer)

        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time:
            points = [p for p in points if p.timestamp <= end_time]
        if tag_name:
            points = [p for p in points if p.tag_name == tag_name]

        return points

    def clear(self) -> None:
        """Clear all data from buffer"""
        with self._lock:
            self._buffer.clear()

    @property
    def size(self) -> int:
        """Current buffer size"""
        with self._lock:
            return len(self._buffer)

    @property
    def is_full(self) -> bool:
        """Check if buffer is full"""
        return self.size >= self._max_size


class TrendLogger:
    """
    Real-time trend logging for PLC data.

    Usage:
        logger = TrendLogger()
        logger.configure(TrendConfig(
            sample_interval_ms=500,
            tags=["Temperature", "Pressure", "Flow"]
        ))
        logger.start(read_callback=plc.read_tag)
        # ... logging runs in background ...
        logger.stop()
        logger.export_csv("trends.csv")
    """

    def __init__(self):
        self._config = TrendConfig()
        self._buffer = TrendBuffer()
        self._running = False
        self._thread: threading.Thread | None = None
        self._read_callback: Callable[[str], Any] | None = None
        self._data_callback: Callable[[TrendDataPoint], None] | None = None
        self._db_connection: sqlite3.Connection | None = None

    def configure(self, config: TrendConfig) -> None:
        """
        Configure the trend logger.

        Args:
            config: Trend configuration
        """
        self._config = config
        self._buffer = TrendBuffer(max_size=config.max_points)

        if config.export_format == ExportFormat.SQLITE and config.export_path:
            self._init_sqlite(config.export_path)

    def _init_sqlite(self, db_path: Path) -> None:
        """Initialize SQLite database for persistent storage"""
        self._db_connection = sqlite3.connect(str(db_path), check_same_thread=False)
        cursor = self._db_connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                tag_name TEXT NOT NULL,
                value TEXT NOT NULL,
                quality TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_timestamp ON trend_data(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trend_tag ON trend_data(tag_name)
        """)
        self._db_connection.commit()

    def start(
        self,
        read_callback: Callable[[str], Any],
        data_callback: Callable[[TrendDataPoint], None] | None = None
    ) -> None:
        """
        Start trend logging.

        Args:
            read_callback: Function to read tag values, signature: (tag_name) -> value
            data_callback: Optional callback for each new data point
        """
        if self._running:
            return

        self._read_callback = read_callback
        self._data_callback = data_callback
        self._running = True
        self._thread = threading.Thread(target=self._logging_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop trend logging"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _logging_loop(self) -> None:
        """Main logging loop - runs in background thread"""
        interval = self._config.sample_interval_ms / 1000.0

        while self._running:
            start_time = time.time()

            for tag_name in self._config.tags:
                try:
                    value = self._read_callback(tag_name)
                    point = TrendDataPoint(
                        timestamp=time.time(),
                        tag_name=tag_name,
                        value=value,
                        quality="Good"
                    )
                except Exception as e:
                    point = TrendDataPoint(
                        timestamp=time.time(),
                        tag_name=tag_name,
                        value=None,
                        quality=f"Bad: {str(e)}"
                    )

                self._buffer.append(point)

                # Notify data callback
                if self._data_callback:
                    try:
                        self._data_callback(point)
                    except Exception:
                        pass

                # Store to SQLite if configured
                if self._db_connection:
                    self._store_point(point)

            # Auto-export if buffer full
            if self._config.auto_export and self._buffer.is_full:
                self._auto_export()

            # Sleep for remaining interval time
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

    def _store_point(self, point: TrendDataPoint) -> None:
        """Store data point to SQLite"""
        if not self._db_connection:
            return

        try:
            cursor = self._db_connection.cursor()
            cursor.execute(
                "INSERT INTO trend_data (timestamp, tag_name, value, quality) VALUES (?, ?, ?, ?)",
                (point.timestamp, point.tag_name, str(point.value), point.quality)
            )
            self._db_connection.commit()
        except Exception:
            pass

    def _auto_export(self) -> None:
        """Automatically export data when buffer full"""
        if not self._config.export_path:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = self._config.export_path

        if self._config.export_format == ExportFormat.CSV:
            path = base_path / f"trend_{timestamp}.csv"
            self.export_csv(path)
        elif self._config.export_format == ExportFormat.JSON:
            path = base_path / f"trend_{timestamp}.json"
            self.export_json(path)

        self._buffer.clear()

    def add_tag(self, tag_name: str) -> None:
        """Add a tag to monitor"""
        if tag_name not in self._config.tags:
            self._config.tags.append(tag_name)

    def remove_tag(self, tag_name: str) -> None:
        """Remove a tag from monitoring"""
        if tag_name in self._config.tags:
            self._config.tags.remove(tag_name)

    def log_value(self, tag_name: str, value: Any, quality: str = "Good") -> None:
        """
        Manually log a value (for use without automatic polling).

        Args:
            tag_name: Name of the tag
            value: Value to log
            quality: Data quality indicator
        """
        point = TrendDataPoint(
            timestamp=time.time(),
            tag_name=tag_name,
            value=value,
            quality=quality
        )
        self._buffer.append(point)

        if self._data_callback:
            self._data_callback(point)

        if self._db_connection:
            self._store_point(point)

    def get_data(
        self,
        tag_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> list[TrendDataPoint]:
        """
        Get trend data from buffer.

        Args:
            tag_name: Optional tag filter
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of data points matching criteria
        """
        start_ts = start_time.timestamp() if start_time else None
        end_ts = end_time.timestamp() if end_time else None
        return self._buffer.get_range(start_ts, end_ts, tag_name)

    def get_latest(self, tag_name: str) -> TrendDataPoint | None:
        """Get the most recent data point for a tag"""
        points = self._buffer.get_by_tag(tag_name)
        return points[-1] if points else None

    def get_statistics(self, tag_name: str) -> dict[str, Any]:
        """
        Get statistics for a tag.

        Returns:
            Dictionary with min, max, avg, count, std_dev
        """
        points = self._buffer.get_by_tag(tag_name)
        values = [p.value for p in points if isinstance(p.value, (int, float))]

        if not values:
            return {"count": 0}

        import statistics as stats

        result = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": stats.mean(values),
        }

        if len(values) > 1:
            result["std_dev"] = stats.stdev(values)

        return result

    def export_csv(self, file_path: str | Path) -> None:
        """
        Export trend data to CSV file.

        Args:
            file_path: Path to output CSV file
        """
        points = self._buffer.get_all()
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "DateTime", "Tag", "Value", "Quality"])
            for point in points:
                writer.writerow([
                    point.timestamp,
                    point.datetime.isoformat(),
                    point.tag_name,
                    point.value,
                    point.quality
                ])

    def export_json(self, file_path: str | Path) -> None:
        """
        Export trend data to JSON file.

        Args:
            file_path: Path to output JSON file
        """
        points = self._buffer.get_all()
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "exported_at": datetime.now().isoformat(),
            "point_count": len(points),
            "tags": list({p.tag_name for p in points}),
            "data": [point.to_dict() for point in points]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def query_historical(
        self,
        tag_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> list[TrendDataPoint]:
        """
        Query historical data from SQLite database.

        Args:
            tag_name: Tag to query
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of data points from database
        """
        if not self._db_connection:
            return []

        cursor = self._db_connection.cursor()
        cursor.execute(
            """
            SELECT timestamp, tag_name, value, quality
            FROM trend_data
            WHERE tag_name = ? AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
            """,
            (tag_name, start_time.timestamp(), end_time.timestamp())
        )

        points = []
        for row in cursor.fetchall():
            try:
                # Try to parse value back to original type
                value = json.loads(row[2])
            except (json.JSONDecodeError, TypeError):
                value = row[2]

            points.append(TrendDataPoint(
                timestamp=row[0],
                tag_name=row[1],
                value=value,
                quality=row[3]
            ))

        return points

    def clear(self) -> None:
        """Clear all buffered data"""
        self._buffer.clear()

    def close(self) -> None:
        """Close the trend logger and cleanup resources"""
        self.stop()
        if self._db_connection:
            self._db_connection.close()
            self._db_connection = None

    @property
    def is_running(self) -> bool:
        """Check if logger is currently running"""
        return self._running

    @property
    def point_count(self) -> int:
        """Current number of data points in buffer"""
        return self._buffer.size

    @property
    def monitored_tags(self) -> list[str]:
        """List of tags being monitored"""
        return list(self._config.tags)
