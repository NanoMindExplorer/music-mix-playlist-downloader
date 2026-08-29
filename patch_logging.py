import re

# Patch downloader.py
with open("downloader.py", "r") as f:
    code = f.read()
if "setup_logging" not in code:
    code = code.replace(
        "    try:\n        run_cli()",
        "    try:\n        from mmpd.logger import setup_logging\n        import logging\n        setup_logging(level=logging.WARNING, enable_console=True)\n        run_cli()"
    )
    with open("downloader.py", "w") as f:
        f.write(code)

# Patch mmpd/__main__.py
with open("mmpd/__main__.py", "r") as f:
    code2 = f.read()
if "setup_logging" not in code2:
    code2 = code2.replace(
        "    try:\n        from downloader import run_cli\n        run_cli()",
        "    try:\n        from downloader import run_cli\n        from mmpd.logger import setup_logging\n        import logging\n        setup_logging(level=logging.WARNING, enable_console=True)\n        run_cli()"
    )
    with open("mmpd/__main__.py", "w") as f:
        f.write(code2)
