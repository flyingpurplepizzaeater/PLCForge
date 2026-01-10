"""
PLCForge - Multi-Vendor PLC Programming Application

Main entry point for the application.
"""

import sys
import os
from pathlib import Path


def setup_environment():
    """Set up application environment"""
    # Add application to path if needed
    app_dir = Path(__file__).parent.parent
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    # Create necessary directories
    config_dir = Path.home() / '.plcforge'
    config_dir.mkdir(exist_ok=True)

    (config_dir / 'audit').mkdir(exist_ok=True)
    (config_dir / 'cache').mkdir(exist_ok=True)
    (config_dir / 'projects').mkdir(exist_ok=True)


def main():
    """Main entry point"""
    setup_environment()

    # Import here to ensure environment is set up
    from plcforge.gui.main_window import main as gui_main

    gui_main()


def cli_main():
    """Command-line interface entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="PLCForge - Multi-Vendor PLC Programming"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # GUI command (default)
    gui_parser = subparsers.add_parser('gui', help='Launch GUI application')

    # Connect command
    connect_parser = subparsers.add_parser('connect', help='Connect to PLC')
    connect_parser.add_argument('ip', help='PLC IP address')
    connect_parser.add_argument('--vendor', '-v', choices=['siemens', 'allen_bradley', 'delta', 'omron'],
                                help='PLC vendor')
    connect_parser.add_argument('--rack', '-r', type=int, default=0, help='Rack number')
    connect_parser.add_argument('--slot', '-s', type=int, default=1, help='Slot number')

    # Read command
    read_parser = subparsers.add_parser('read', help='Read tag from PLC')
    read_parser.add_argument('ip', help='PLC IP address')
    read_parser.add_argument('tag', help='Tag name to read')
    read_parser.add_argument('--vendor', '-v', help='PLC vendor')

    # Write command
    write_parser = subparsers.add_parser('write', help='Write tag to PLC')
    write_parser.add_argument('ip', help='PLC IP address')
    write_parser.add_argument('tag', help='Tag name to write')
    write_parser.add_argument('value', help='Value to write')
    write_parser.add_argument('--vendor', '-v', help='PLC vendor')

    # Recovery command
    recovery_parser = subparsers.add_parser('recover', help='Password recovery')
    recovery_parser.add_argument('file', help='Project file path')
    recovery_parser.add_argument('--vendor', '-v', required=True, help='PLC vendor')
    recovery_parser.add_argument('--method', '-m', nargs='+',
                                 choices=['file', 'dictionary', 'bruteforce', 'vulnerability'],
                                 default=['file', 'dictionary'],
                                 help='Recovery methods to use')
    recovery_parser.add_argument('--wordlist', '-w', help='Custom wordlist path')
    recovery_parser.add_argument('--confirm', action='store_true',
                                 help='Confirm authorization (required)')

    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan network for PLCs')
    scan_parser.add_argument('subnet', help='Subnet to scan (e.g., 192.168.1.0/24)')

    args = parser.parse_args()

    setup_environment()

    if args.command is None or args.command == 'gui':
        main()

    elif args.command == 'connect':
        from plcforge.pal.unified_api import connect
        try:
            plc = connect(args.ip, vendor=args.vendor)
            print(f"Connected to {plc.info.vendor} {plc.info.model}")
            print(f"Mode: {plc.mode.value}")
            print(f"Firmware: {plc.info.firmware}")
            plc.disconnect()
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit(1)

    elif args.command == 'read':
        from plcforge.pal.unified_api import connect
        try:
            plc = connect(args.ip, vendor=args.vendor)
            value = plc.read(args.tag)
            print(f"{args.tag} = {value}")
            plc.disconnect()
        except Exception as e:
            print(f"Read failed: {e}")
            sys.exit(1)

    elif args.command == 'write':
        from plcforge.pal.unified_api import connect
        try:
            plc = connect(args.ip, vendor=args.vendor)
            success = plc.write(args.tag, args.value)
            if success:
                print(f"Wrote {args.value} to {args.tag}")
            else:
                print("Write failed")
                sys.exit(1)
            plc.disconnect()
        except Exception as e:
            print(f"Write failed: {e}")
            sys.exit(1)

    elif args.command == 'recover':
        if not args.confirm:
            print("ERROR: You must confirm authorization with --confirm flag")
            print("This confirms you are authorized to recover this password.")
            sys.exit(1)

        from plcforge.recovery.engine import (
            RecoveryEngine, RecoveryTarget, RecoveryConfig, RecoveryMethod
        )

        method_map = {
            'file': RecoveryMethod.FILE_PARSE,
            'dictionary': RecoveryMethod.DICTIONARY,
            'bruteforce': RecoveryMethod.BRUTEFORCE,
            'vulnerability': RecoveryMethod.VULNERABILITY,
        }

        methods = [method_map[m] for m in args.method]

        config = RecoveryConfig(
            methods=methods,
            wordlist_path=args.wordlist,
        )

        target = RecoveryTarget(
            target_type="backup_file",
            vendor=args.vendor,
            model="",
            protection_type="project",
            file_path=args.file,
        )

        print(f"Starting password recovery for {args.file}")
        print(f"Methods: {', '.join(args.method)}")
        print()

        engine = RecoveryEngine()
        result = engine.recover(target, config, authorization_confirmed=True)

        if result.status.value == "success":
            print(f"SUCCESS! Password: {result.password}")
            print(f"Method: {result.method_used.value if result.method_used else 'N/A'}")
            print(f"Attempts: {result.attempts}")
        else:
            print(f"FAILED: {result.error_message}")
            print(f"Attempts: {result.attempts}")
            sys.exit(1)

    elif args.command == 'scan':
        from plcforge.pal.unified_api import NetworkScanner

        print(f"Scanning {args.subnet}...")
        devices = NetworkScanner.scan_subnet(args.subnet)

        if devices:
            print(f"\nFound {len(devices)} device(s):\n")
            for device in devices:
                print(f"  {device.ip}: {device.vendor.value} - {device.model}")
        else:
            print("No PLC devices found")


if __name__ == "__main__":
    cli_main()
