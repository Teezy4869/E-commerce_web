"""COGU Fashion storefront demonstration launcher."""

import argparse
import os
import re
import sys
import webbrowser
from pathlib import Path
from presentation.web_server import create_web_server


def load_local_env(path=None):
    """Load simple KEY=value settings from a local .env without overriding the shell."""
    config = Path(path) if path is not None else Path(__file__).with_name(".env")
    if not config.is_file():
        return
    for raw in config.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def main():
    load_local_env()
    parser = argparse.ArgumentParser(description="COGU Fashion storefront demo")
    parser.add_argument("--port", type=int, default=8080, help="Port to run web server on (default: 8080)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()

    # Try binding to requested port, fallback to alternative if occupied
    port = args.port
    server = None
    for attempt in range(5):
        try:
            server = create_web_server(port=port, host=args.host)
            break
        except OSError:
            print(f"  [Warning] Port {port} is in use. Trying {port + 1}...")
            port += 1

    if server is None:
        print("  [Error] Could not bind to an available port. Exiting.")
        sys.exit(1)

    url = f"http://{args.host}:{port}/"

    print("=" * 65)
    print("  COGU FASHION — STOREFRONT DEMONSTRATION")
    print("  PTIT Assignment 06: Three-Layer Architecture")
    print("=" * 65)
    print(f"  Web Server URL : {url}")
    print(f"  Catalogue      : {url}shop")
    print(f"  AI Studio      : {url}studio")
    print(f"  Account / Cart : {url}account | {url}cart")
    print(f"  Staff dashboard: {url}admin (provision accounts with scripts/seed_admin_demo.py)")
    print("  Product sample : /product?slug=ao-thun-oversize-essential")
    print("  Status         : Ready & Listening")
    print("  Search Modes   : Text Search (UC-02)")
    print("                   Voice Search (UC-03)")
    print("                   Image Search (UC-04)")
    print("                   Order Search (UC-05)")
    print("  Architecture   : Presentation -> Application -> Data")
    print("  Outfit Preview : Configured provider or clearly labeled DEMO samples")
    if not os.environ.get("COGU_ADMIN_TOKEN"):
        print("  Legacy admin order demo : Disabled (set COGU_ADMIN_TOKEN to enable)")
    print("=" * 65)
    print("  Press Ctrl+C to stop the server.\n")

    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Shutting down COGU Fashion Web Server...")
    finally:
        server.server_close()
        print("  Server stopped cleanly.")


if __name__ == "__main__":
    main()
