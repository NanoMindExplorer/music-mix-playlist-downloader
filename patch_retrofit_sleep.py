with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

code = code.replace(
    "            progress.advance(main_task)",
    "            progress.advance(main_task)\n            import time\n            time.sleep(1)  # D3: jeda 1 detik antar lagu agar tidak rate-limit API"
)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
