"""
Password Recovery Engine

Orchestrates password recovery across multiple methods:
- File parsing (extract from backup files)
- Dictionary attacks
- Brute-force attacks
- Vulnerability exploits
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
import threading
import hashlib
import itertools
import string
import time

from plcforge.drivers.base import PLCDevice


class RecoveryMethod(Enum):
    """Available recovery methods"""
    FILE_PARSE = "file_parse"
    DICTIONARY = "dictionary"
    BRUTEFORCE = "bruteforce"
    VULNERABILITY = "vulnerability"


class RecoveryStatus(Enum):
    """Status of recovery operation"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RecoveryTarget:
    """Target for password recovery"""
    target_type: str  # "online_plc" or "backup_file"
    vendor: str
    model: str
    protection_type: str  # "cpu", "project", "block"
    file_path: Optional[str] = None
    device: Optional[PLCDevice] = None
    ip_address: Optional[str] = None


@dataclass
class RecoveryConfig:
    """Configuration for recovery operation"""
    methods: List[RecoveryMethod] = field(default_factory=lambda: [RecoveryMethod.FILE_PARSE])
    wordlist_path: Optional[str] = None
    custom_wordlist: Optional[List[str]] = None
    max_attempts: int = 1_000_000
    charset: str = "alphanumeric"  # "numeric", "alpha", "alphanumeric", "all", "custom"
    custom_charset: Optional[str] = None
    min_length: int = 1
    max_length: int = 8
    use_gpu: bool = False
    rate_limit_ms: int = 0  # Delay between online attempts
    callback: Optional[Callable] = None  # Progress callback


@dataclass
class RecoveryResult:
    """Result of password recovery attempt"""
    status: RecoveryStatus
    password: Optional[str] = None
    method_used: Optional[RecoveryMethod] = None
    attempts: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryProgress:
    """Progress information during recovery"""
    method: RecoveryMethod
    attempts: int
    total_possible: int
    current_password: str
    elapsed_seconds: float
    rate_per_second: float
    estimated_remaining_seconds: Optional[float]


class RecoveryEngine:
    """
    Main password recovery engine.

    Orchestrates multiple recovery methods and tracks progress.
    """

    def __init__(self):
        self._running = False
        self._cancel_flag = False
        self._current_method: Optional[RecoveryMethod] = None
        self._progress_callback: Optional[Callable] = None
        self._start_time: Optional[datetime] = None
        self._attempts = 0

    def recover(
        self,
        target: RecoveryTarget,
        config: RecoveryConfig,
        authorization_confirmed: bool = False
    ) -> RecoveryResult:
        """
        Attempt to recover password using configured methods.

        Args:
            target: Recovery target (file or PLC)
            config: Recovery configuration
            authorization_confirmed: Must be True to proceed

        Returns:
            RecoveryResult with outcome
        """
        # Require authorization confirmation
        if not authorization_confirmed:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                error_message="Authorization not confirmed. User must explicitly confirm they are authorized."
            )

        self._running = True
        self._cancel_flag = False
        self._progress_callback = config.callback
        self._start_time = datetime.now()
        self._attempts = 0

        result = RecoveryResult(status=RecoveryStatus.RUNNING)

        try:
            # Try each method in order
            for method in config.methods:
                if self._cancel_flag:
                    result.status = RecoveryStatus.CANCELLED
                    break

                self._current_method = method
                method_result = self._try_method(method, target, config)

                if method_result.status == RecoveryStatus.SUCCESS:
                    return method_result

            # No method succeeded
            if result.status != RecoveryStatus.CANCELLED:
                result.status = RecoveryStatus.FAILED
                result.error_message = "All recovery methods exhausted without success"

        except Exception as e:
            result.status = RecoveryStatus.FAILED
            result.error_message = str(e)

        finally:
            self._running = False
            result.attempts = self._attempts
            if self._start_time:
                result.duration_seconds = (datetime.now() - self._start_time).total_seconds()

        return result

    def cancel(self):
        """Cancel ongoing recovery operation"""
        self._cancel_flag = True

    def is_running(self) -> bool:
        """Check if recovery is in progress"""
        return self._running

    def _try_method(
        self,
        method: RecoveryMethod,
        target: RecoveryTarget,
        config: RecoveryConfig
    ) -> RecoveryResult:
        """Try a specific recovery method"""
        if method == RecoveryMethod.FILE_PARSE:
            return self._try_file_parse(target, config)
        elif method == RecoveryMethod.DICTIONARY:
            return self._try_dictionary(target, config)
        elif method == RecoveryMethod.BRUTEFORCE:
            return self._try_bruteforce(target, config)
        elif method == RecoveryMethod.VULNERABILITY:
            return self._try_vulnerability(target, config)
        else:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                error_message=f"Unknown method: {method}"
            )

    def _try_file_parse(
        self,
        target: RecoveryTarget,
        config: RecoveryConfig
    ) -> RecoveryResult:
        """Try to extract password from backup file"""
        if target.target_type != "backup_file" or not target.file_path:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                error_message="File parsing requires backup file path"
            )

        from plcforge.recovery.file_parsers import get_parser

        try:
            parser = get_parser(target.vendor, target.file_path)
            if parser is None:
                return RecoveryResult(
                    status=RecoveryStatus.FAILED,
                    error_message=f"No parser available for vendor: {target.vendor}"
                )

            result = parser.extract_password(target.file_path, target.protection_type)

            if result.get('password'):
                return RecoveryResult(
                    status=RecoveryStatus.SUCCESS,
                    password=result['password'],
                    method_used=RecoveryMethod.FILE_PARSE,
                    details=result
                )
            elif result.get('hash'):
                # Got hash, can try to crack it offline
                return RecoveryResult(
                    status=RecoveryStatus.FAILED,
                    error_message="Got password hash but could not crack it",
                    details=result
                )
            else:
                return RecoveryResult(
                    status=RecoveryStatus.FAILED,
                    error_message="No password information found in file"
                )

        except Exception as e:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                error_message=f"File parse error: {str(e)}"
            )

    def _try_dictionary(
        self,
        target: RecoveryTarget,
        config: RecoveryConfig
    ) -> RecoveryResult:
        """Try dictionary attack"""
        # Get wordlist
        wordlist = []

        if config.custom_wordlist:
            wordlist = config.custom_wordlist
        elif config.wordlist_path:
            try:
                with open(config.wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                    wordlist = [line.strip() for line in f if line.strip()]
            except Exception as e:
                return RecoveryResult(
                    status=RecoveryStatus.FAILED,
                    error_message=f"Could not load wordlist: {str(e)}"
                )
        else:
            # Use default industrial wordlist
            wordlist = self._get_default_wordlist()

        # Try each password
        total = len(wordlist)
        start_time = time.time()

        for i, password in enumerate(wordlist):
            if self._cancel_flag:
                return RecoveryResult(status=RecoveryStatus.CANCELLED)

            self._attempts += 1

            # Report progress
            if self._progress_callback and i % 100 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (total - i) / rate if rate > 0 else None

                self._progress_callback(RecoveryProgress(
                    method=RecoveryMethod.DICTIONARY,
                    attempts=i,
                    total_possible=total,
                    current_password=password[:4] + "****",
                    elapsed_seconds=elapsed,
                    rate_per_second=rate,
                    estimated_remaining_seconds=remaining
                ))

            # Try the password
            if self._verify_password(target, password, config):
                return RecoveryResult(
                    status=RecoveryStatus.SUCCESS,
                    password=password,
                    method_used=RecoveryMethod.DICTIONARY,
                    attempts=i + 1,
                    duration_seconds=time.time() - start_time
                )

            # Rate limiting for online attempts
            if config.rate_limit_ms > 0:
                time.sleep(config.rate_limit_ms / 1000.0)

        return RecoveryResult(
            status=RecoveryStatus.FAILED,
            error_message="Dictionary exhausted without match",
            attempts=total
        )

    def _try_bruteforce(
        self,
        target: RecoveryTarget,
        config: RecoveryConfig
    ) -> RecoveryResult:
        """Try brute-force attack"""
        # Determine charset
        charset = self._get_charset(config)

        # Calculate total possibilities
        total = sum(
            len(charset) ** length
            for length in range(config.min_length, config.max_length + 1)
        )

        if total > config.max_attempts:
            # Warn but continue up to max_attempts
            pass

        start_time = time.time()
        attempts = 0

        for length in range(config.min_length, config.max_length + 1):
            if self._cancel_flag:
                return RecoveryResult(status=RecoveryStatus.CANCELLED)

            for password_tuple in itertools.product(charset, repeat=length):
                if self._cancel_flag:
                    return RecoveryResult(status=RecoveryStatus.CANCELLED)

                if attempts >= config.max_attempts:
                    return RecoveryResult(
                        status=RecoveryStatus.FAILED,
                        error_message=f"Max attempts ({config.max_attempts}) reached",
                        attempts=attempts
                    )

                password = ''.join(password_tuple)
                attempts += 1
                self._attempts += 1

                # Progress callback
                if self._progress_callback and attempts % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = attempts / elapsed if elapsed > 0 else 0
                    remaining = (min(total, config.max_attempts) - attempts) / rate if rate > 0 else None

                    self._progress_callback(RecoveryProgress(
                        method=RecoveryMethod.BRUTEFORCE,
                        attempts=attempts,
                        total_possible=min(total, config.max_attempts),
                        current_password=password[:2] + "****",
                        elapsed_seconds=elapsed,
                        rate_per_second=rate,
                        estimated_remaining_seconds=remaining
                    ))

                # Verify password
                if self._verify_password(target, password, config):
                    return RecoveryResult(
                        status=RecoveryStatus.SUCCESS,
                        password=password,
                        method_used=RecoveryMethod.BRUTEFORCE,
                        attempts=attempts,
                        duration_seconds=time.time() - start_time
                    )

                # Rate limiting
                if config.rate_limit_ms > 0:
                    time.sleep(config.rate_limit_ms / 1000.0)

        return RecoveryResult(
            status=RecoveryStatus.FAILED,
            error_message="Bruteforce exhausted without match",
            attempts=attempts
        )

    def _try_vulnerability(
        self,
        target: RecoveryTarget,
        config: RecoveryConfig
    ) -> RecoveryResult:
        """Try known vulnerability exploits"""
        from plcforge.recovery.vulnerabilities import get_exploits

        exploits = get_exploits(target.vendor, target.model)

        if not exploits:
            return RecoveryResult(
                status=RecoveryStatus.FAILED,
                error_message=f"No known vulnerabilities for {target.vendor} {target.model}"
            )

        for exploit in exploits:
            if self._cancel_flag:
                return RecoveryResult(status=RecoveryStatus.CANCELLED)

            try:
                result = exploit.execute(target)
                if result.get('success') and result.get('password'):
                    return RecoveryResult(
                        status=RecoveryStatus.SUCCESS,
                        password=result['password'],
                        method_used=RecoveryMethod.VULNERABILITY,
                        details={'exploit': exploit.__class__.__name__}
                    )
            except Exception as e:
                # Continue to next exploit
                pass

        return RecoveryResult(
            status=RecoveryStatus.FAILED,
            error_message="No vulnerabilities successfully exploited"
        )

    def _verify_password(
        self,
        target: RecoveryTarget,
        password: str,
        config: RecoveryConfig
    ) -> bool:
        """Verify if password is correct"""
        if target.target_type == "online_plc" and target.device:
            # Try to authenticate with PLC
            try:
                return target.device.authenticate(password)
            except Exception:
                return False

        elif target.target_type == "backup_file" and target.file_path:
            # Verify against file
            from plcforge.recovery.file_parsers import get_parser
            parser = get_parser(target.vendor, target.file_path)
            if parser:
                return parser.verify_password(target.file_path, password, target.protection_type)

        return False

    def _get_charset(self, config: RecoveryConfig) -> str:
        """Get character set for bruteforce"""
        if config.charset == "numeric":
            return string.digits
        elif config.charset == "alpha":
            return string.ascii_letters
        elif config.charset == "alphanumeric":
            return string.ascii_letters + string.digits
        elif config.charset == "all":
            return string.printable.strip()
        elif config.charset == "custom" and config.custom_charset:
            return config.custom_charset
        else:
            return string.ascii_letters + string.digits

    def _get_default_wordlist(self) -> List[str]:
        """Get default industrial password wordlist"""
        # Common industrial/PLC passwords
        return [
            # Numeric
            "0000", "1111", "1234", "12345", "123456", "0001", "0002",
            "1000", "2000", "3000", "4000", "5000",
            "9999", "8888", "7777", "6666",

            # Vendor defaults
            "siemens", "SIEMENS", "simatic", "SIMATIC",
            "allen", "ALLEN", "bradley", "BRADLEY", "rockwell", "ROCKWELL",
            "delta", "DELTA", "omron", "OMRON",
            "plc", "PLC", "admin", "ADMIN", "user", "USER",
            "password", "PASSWORD", "pass", "PASS",

            # Common words
            "system", "SYSTEM", "control", "CONTROL",
            "machine", "MACHINE", "robot", "ROBOT",
            "motor", "MOTOR", "pump", "PUMP",
            "line1", "LINE1", "line2", "LINE2",
            "test", "TEST", "demo", "DEMO",
            "default", "DEFAULT",
            "maintenance", "MAINTENANCE",
            "operator", "OPERATOR",
            "engineer", "ENGINEER",
            "service", "SERVICE",

            # Year-based
            "2020", "2021", "2022", "2023", "2024", "2025", "2026",

            # Keyboard patterns
            "qwerty", "QWERTY", "asdfgh", "ASDFGH",
            "qwertz", "QWERTZ",  # German keyboard

            # Empty/blank
            "", " ",
        ]
