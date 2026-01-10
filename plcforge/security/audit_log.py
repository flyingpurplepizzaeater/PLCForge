"""
Security Audit Logging

Provides tamper-evident logging for all security-sensitive operations.
Logs are stored locally and can be exported for compliance reporting.
"""

import hashlib
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class AuditEntry:
    """A single audit log entry"""
    timestamp: str
    event_id: str
    user: str
    machine_id: str
    action: str
    target: dict[str, Any]
    result: str  # "success", "failure", "cancelled"
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: int | None = None
    previous_hash: str | None = None
    entry_hash: str | None = None

    def compute_hash(self) -> str:
        """Compute hash of entry for integrity verification"""
        data = {
            'timestamp': self.timestamp,
            'event_id': self.event_id,
            'user': self.user,
            'machine_id': self.machine_id,
            'action': self.action,
            'target': self.target,
            'result': self.result,
            'details': self.details,
            'duration_ms': self.duration_ms,
            'previous_hash': self.previous_hash,
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()


class AuditLogger:
    """
    Tamper-evident audit logger.

    Features:
    - Chain-linked entries (each entry contains hash of previous)
    - Local file storage with rotation
    - Export to JSON for compliance reporting
    - Thread-safe operation
    """

    def __init__(self, log_dir: str | None = None):
        self.log_dir = Path(log_dir) if log_dir else Path.home() / '.plcforge' / 'audit'
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._current_log_file: Path | None = None
        self._last_hash: str | None = None
        self._lock = threading.Lock()
        self._machine_id = self._get_machine_id()
        self._user = self._get_current_user()

        # Initialize or load existing log
        self._initialize_log()

    def _get_machine_id(self) -> str:
        """Get unique machine identifier"""
        try:
            # Try to get a hardware-based ID
            import platform
            system = platform.system()

            if system == "Windows":
                import subprocess
                result = subprocess.run(
                    ['wmic', 'csproduct', 'get', 'UUID'],
                    capture_output=True, text=True
                )
                uuid_line = result.stdout.strip().split('\n')[-1]
                return uuid_line.strip()

            elif system == "Linux":
                try:
                    with open('/etc/machine-id') as f:
                        return f.read().strip()
                except FileNotFoundError:
                    pass

            elif system == "Darwin":
                import subprocess
                result = subprocess.run(
                    ['system_profiler', 'SPHardwareDataType'],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID' in line:
                        return line.split(':')[-1].strip()

        except Exception:
            pass

        # Fallback: generate and store a UUID
        id_file = self.log_dir / '.machine_id'
        if id_file.exists():
            return id_file.read_text().strip()
        else:
            new_id = str(uuid.uuid4())
            id_file.write_text(new_id)
            return new_id

    def _get_current_user(self) -> str:
        """Get current username"""
        try:
            import getpass
            return getpass.getuser()
        except Exception:
            return "unknown"

    def _initialize_log(self):
        """Initialize or continue existing log file"""
        today = datetime.now().strftime('%Y-%m-%d')
        self._current_log_file = self.log_dir / f'audit_{today}.jsonl'

        # Load last hash if continuing existing file
        if self._current_log_file.exists():
            try:
                with open(self._current_log_file) as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            self._last_hash = entry.get('entry_hash')
            except Exception:
                pass

    def log(
        self,
        action: str,
        target: dict[str, Any],
        result: str = "success",
        details: dict[str, Any] | None = None,
        duration_ms: int | None = None
    ) -> AuditEntry:
        """
        Log a security-sensitive action.

        Args:
            action: Action type (e.g., "password_recovery", "plc_connect")
            target: Target information (device, file, etc.)
            result: Outcome ("success", "failure", "cancelled")
            details: Additional details
            duration_ms: Operation duration in milliseconds

        Returns:
            The created audit entry
        """
        with self._lock:
            # Create entry
            entry = AuditEntry(
                timestamp=datetime.utcnow().isoformat() + 'Z',
                event_id=str(uuid.uuid4()),
                user=self._user,
                machine_id=self._machine_id,
                action=action,
                target=target,
                result=result,
                details=details or {},
                duration_ms=duration_ms,
                previous_hash=self._last_hash,
            )

            # Compute hash
            entry.entry_hash = entry.compute_hash()
            self._last_hash = entry.entry_hash

            # Write to file
            self._write_entry(entry)

            return entry

    def _write_entry(self, entry: AuditEntry):
        """Write entry to log file"""
        # Check for date rotation
        today = datetime.now().strftime('%Y-%m-%d')
        expected_file = self.log_dir / f'audit_{today}.jsonl'

        if self._current_log_file != expected_file:
            self._current_log_file = expected_file

        # Append to file
        with open(self._current_log_file, 'a') as f:
            json.dump(asdict(entry), f)
            f.write('\n')

    def log_password_recovery(
        self,
        target_type: str,
        target_id: str,
        vendor: str,
        method: str,
        success: bool,
        duration_ms: int,
        password_hash: str | None = None
    ) -> AuditEntry:
        """Log a password recovery attempt"""
        return self.log(
            action="password_recovery",
            target={
                'type': target_type,
                'identifier': target_id,
                'vendor': vendor,
            },
            result="success" if success else "failure",
            details={
                'method': method,
                'password_hash': password_hash,  # Store hash, never plaintext
            },
            duration_ms=duration_ms,
        )

    def log_plc_connection(
        self,
        ip: str,
        vendor: str,
        model: str,
        success: bool
    ) -> AuditEntry:
        """Log PLC connection attempt"""
        return self.log(
            action="plc_connect",
            target={
                'type': 'plc',
                'ip': ip,
                'vendor': vendor,
                'model': model,
            },
            result="success" if success else "failure",
        )

    def log_program_download(
        self,
        ip: str,
        vendor: str,
        success: bool
    ) -> AuditEntry:
        """Log program download to PLC"""
        return self.log(
            action="program_download",
            target={
                'type': 'plc',
                'ip': ip,
                'vendor': vendor,
            },
            result="success" if success else "failure",
        )

    def log_authorization(
        self,
        action: str,
        acknowledged: bool
    ) -> AuditEntry:
        """Log user authorization acknowledgment"""
        return self.log(
            action="authorization_acknowledgment",
            target={'requested_action': action},
            result="acknowledged" if acknowledged else "declined",
        )

    def get_entries(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        action_filter: str | None = None,
        limit: int = 1000
    ) -> list[AuditEntry]:
        """
        Retrieve audit entries.

        Args:
            start_date: Filter entries after this date
            end_date: Filter entries before this date
            action_filter: Filter by action type
            limit: Maximum entries to return

        Returns:
            List of matching audit entries
        """
        entries = []

        # Get relevant log files
        log_files = sorted(self.log_dir.glob('audit_*.jsonl'))

        for log_file in log_files:
            # Quick date check from filename
            file_date_str = log_file.stem.replace('audit_', '')
            try:
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if start_date and file_date.date() < start_date.date():
                    continue
                if end_date and file_date.date() > end_date.date():
                    continue
            except ValueError:
                continue

            # Read entries
            try:
                with open(log_file) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            entry = AuditEntry(**data)

                            # Apply filters
                            if action_filter and entry.action != action_filter:
                                continue

                            entry_time = datetime.fromisoformat(
                                entry.timestamp.replace('Z', '+00:00')
                            )
                            if start_date and entry_time < start_date:
                                continue
                            if end_date and entry_time > end_date:
                                continue

                            entries.append(entry)

                            if len(entries) >= limit:
                                return entries

            except Exception:
                continue

        return entries

    def verify_integrity(self) -> dict[str, Any]:
        """
        Verify integrity of audit log chain.

        Returns:
            Dict with verification results
        """
        result = {
            'valid': True,
            'total_entries': 0,
            'broken_chains': [],
            'modified_entries': [],
        }

        previous_hash = None

        for log_file in sorted(self.log_dir.glob('audit_*.jsonl')):
            try:
                with open(log_file) as f:
                    for line_num, line in enumerate(f, 1):
                        if not line.strip():
                            continue

                        data = json.loads(line)
                        entry = AuditEntry(**data)
                        result['total_entries'] += 1

                        # Check chain
                        if entry.previous_hash != previous_hash:
                            result['valid'] = False
                            result['broken_chains'].append({
                                'file': str(log_file),
                                'line': line_num,
                                'expected': previous_hash,
                                'found': entry.previous_hash,
                            })

                        # Verify hash
                        computed_hash = entry.compute_hash()
                        if computed_hash != entry.entry_hash:
                            result['valid'] = False
                            result['modified_entries'].append({
                                'file': str(log_file),
                                'line': line_num,
                                'event_id': entry.event_id,
                            })

                        previous_hash = entry.entry_hash

            except Exception as e:
                result['valid'] = False
                result['errors'] = result.get('errors', [])
                result['errors'].append({
                    'file': str(log_file),
                    'error': str(e),
                })

        return result

    def export_report(
        self,
        output_path: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        format: str = "json"
    ) -> str:
        """
        Export audit log for compliance reporting.

        Args:
            output_path: Output file path
            start_date: Start of report period
            end_date: End of report period
            format: Output format ("json" or "csv")

        Returns:
            Path to exported file
        """
        entries = self.get_entries(start_date, end_date, limit=100000)
        integrity = self.verify_integrity()

        if format == "json":
            report = {
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'report_period': {
                    'start': start_date.isoformat() if start_date else None,
                    'end': end_date.isoformat() if end_date else None,
                },
                'integrity_check': integrity,
                'total_entries': len(entries),
                'entries': [asdict(e) for e in entries],
            }

            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)

        elif format == "csv":
            import csv

            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Event ID', 'User', 'Machine',
                    'Action', 'Target', 'Result', 'Duration (ms)'
                ])

                for entry in entries:
                    writer.writerow([
                        entry.timestamp,
                        entry.event_id,
                        entry.user,
                        entry.machine_id,
                        entry.action,
                        json.dumps(entry.target),
                        entry.result,
                        entry.duration_ms,
                    ])

        return output_path


# Global logger instance
_logger: AuditLogger | None = None


def get_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _logger
    if _logger is None:
        _logger = AuditLogger()
    return _logger
