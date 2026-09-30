#!/usr/bin/env python3
"""
Music Mix & Playlist Downloader — Web Browser Launcher.

Jalankan perintah ini:
    python web_app.py

Lalu buka browser Anda di:
    http://localhost:5000
    (atau http://<IP_WIFI>:5000 dari HP Android/iPhone Anda)
"""

from __future__ import annotations

import argparse
import sys

from mmpd.web import run_server


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Jalankan Web Browser GUI untuk Music Mix & Playlist Downloader."
    )
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="Host listen (default: 0.0.0.0 agar bisa diakses dari HP di jaringan WiFi yang sama)"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=5000,
        help="Port server (default: 5000)"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Jangan otomatis buka browser saat server dijalankan"
    )

    args = parser.parse_args()

    try:
        run_server(host=args.host, port=args.port, open_browser=not args.no_browser)
    except KeyboardInterrupt:
        print("\n\n👋 Server Web MMPD dihentikan. Sampai jumpa!")
        sys.exit(0)


if __name__ == "__main__":
    main()
