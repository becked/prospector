#!/usr/bin/env python3
"""Management script for the tournament visualizer server.

This script provides commands to start, stop, restart, and check the status
of the development server.
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Port configuration
PORT = 8050
PID_FILE = Path(".server.pid")


def get_pid_from_port() -> int | None:
    """Get the process ID using the configured port.
    
    Returns:
        Process ID if found, None otherwise
    """
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{PORT}"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split()[0])
    except (subprocess.SubprocessError, ValueError):
        pass
    return None


def get_saved_pid() -> int | None:
    """Get the saved process ID from the PID file.
    
    Returns:
        Process ID if file exists and contains valid PID, None otherwise
    """
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process is still running
            os.kill(pid, 0)  # This doesn't kill, just checks if process exists
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            # Clean up stale PID file
            PID_FILE.unlink(missing_ok=True)
    return None


def stop_server(quiet: bool = False) -> bool:
    """Stop the running server.
    
    Args:
        quiet: If True, suppress output messages
        
    Returns:
        True if server was stopped or wasn't running, False on error
    """
    # Try saved PID first
    pid = get_saved_pid()
    
    # Fall back to port lookup
    if pid is None:
        pid = get_pid_from_port()
    
    if pid is None:
        if not quiet:
            print("No server process found")
        PID_FILE.unlink(missing_ok=True)
        return True
    
    try:
        if not quiet:
            print(f"Stopping server (PID: {pid})...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to terminate
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                # Process has terminated
                break
        else:
            # Force kill if still running
            if not quiet:
                print("Force killing server...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
        
        PID_FILE.unlink(missing_ok=True)
        if not quiet:
            print("Server stopped")
        return True
        
    except ProcessLookupError:
        if not quiet:
            print("Server process not found")
        PID_FILE.unlink(missing_ok=True)
        return True
    except PermissionError:
        print(f"Permission denied when trying to stop process {pid}")
        return False
    except Exception as e:
        print(f"Error stopping server: {e}")
        return False


def start_server(debug: bool = True, background: bool = True) -> bool:
    """Start the development server.
    
    Args:
        debug: If True, enable debug mode with auto-reload
        background: If True, run in background; if False, run in foreground
        
    Returns:
        True if server started successfully, False on error
    """
    # Check if server is already running
    pid = get_saved_pid() or get_pid_from_port()
    if pid:
        print(f"Server is already running (PID: {pid}) on http://localhost:{PORT}")
        return False
    
    print(f"Starting server on http://localhost:{PORT}...")
    
    if debug:
        print("Debug mode enabled - server will auto-reload on code changes")
        os.environ["FLASK_DEBUG"] = "1"
    
    try:
        if background:
            # Start in background
            process = subprocess.Popen(
                ["uv", "run", "python", "tournament_visualizer/app.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # Save PID
            PID_FILE.write_text(str(process.pid))
            
            # Wait a moment to check if it started successfully
            time.sleep(2)
            
            if get_pid_from_port():
                print(f"Server started successfully (PID: {process.pid})")
                print(f"Visit http://localhost:{PORT} in your browser")
                return True
            else:
                print("Server failed to start - check logs for errors")
                PID_FILE.unlink(missing_ok=True)
                return False
        else:
            # Run in foreground
            print("Running in foreground mode (press Ctrl+C to stop)...")
            result = subprocess.run(
                ["uv", "run", "python", "tournament_visualizer/app.py"],
                check=False
            )
            return result.returncode == 0
            
    except Exception as e:
        print(f"Error starting server: {e}")
        PID_FILE.unlink(missing_ok=True)
        return False


def restart_server(debug: bool = True) -> bool:
    """Restart the development server.
    
    Args:
        debug: If True, enable debug mode with auto-reload
        
    Returns:
        True if server restarted successfully, False on error
    """
    print("Restarting server...")
    stop_server(quiet=True)
    time.sleep(1)
    return start_server(debug=debug)


def show_status() -> None:
    """Show the current server status."""
    pid = get_saved_pid() or get_pid_from_port()
    
    if pid:
        print(f"Server is running (PID: {pid})")
        print(f"URL: http://localhost:{PORT}")
        
        # Show recent log entries
        log_dir = Path("logs")
        if log_dir.exists():
            log_files = sorted(log_dir.glob("tournament_visualizer_*.log"))
            if log_files:
                latest_log = log_files[-1]
                print(f"Latest log: {latest_log}")
    else:
        print("Server is not running")


def show_logs(follow: bool = False) -> None:
    """Show server logs.
    
    Args:
        follow: If True, continuously tail the log file
    """
    log_dir = Path("logs")
    if not log_dir.exists():
        print("No logs directory found")
        return
    
    log_files = sorted(log_dir.glob("tournament_visualizer_*.log"))
    if not log_files:
        print("No log files found")
        return
    
    latest_log = log_files[-1]
    print(f"Showing log: {latest_log}\n")
    
    if follow:
        try:
            subprocess.run(["tail", "-f", str(latest_log)])
        except KeyboardInterrupt:
            print("\nStopped following log")
    else:
        print(latest_log.read_text())


def main() -> int:
    """Main entry point for the management script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Manage the tournament visualizer development server",
        epilog="Example: uv run python manage.py start"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the server")
    start_parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable debug mode (no auto-reload)"
    )
    start_parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run in foreground (don't daemonize)"
    )

    # Stop command
    subparsers.add_parser("stop", help="Stop the server")

    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart the server")
    restart_parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable debug mode (no auto-reload)"
    )
    
    # Status command
    subparsers.add_parser("status", help="Show server status")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show server logs")
    logs_parser.add_argument(
        "--follow", "-f",
        action="store_true",
        help="Follow log output (like tail -f)"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "start":
            success = start_server(
                debug=not args.no_debug,
                background=not args.foreground
            )
            return 0 if success else 1

        elif args.command == "stop":
            success = stop_server()
            return 0 if success else 1

        elif args.command == "restart":
            success = restart_server(debug=not args.no_debug)
            return 0 if success else 1
            
        elif args.command == "status":
            show_status()
            return 0
            
        elif args.command == "logs":
            show_logs(follow=args.follow)
            return 0
            
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
