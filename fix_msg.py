with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

old_logic = """    # Peringatan jika lirik tidak ditemukan
    if not os.path.exists(lrc_path):
        progress.stop()
        console.print(
            f"[bold yellow]⚠️ Lirik dilewati: Video YouTube tidak memiliki CC untuk {title[:30]}...[/bold yellow]"
        )
        progress.start()"""

new_logic = """    # Peringatan jika lirik tidak ditemukan
    if not os.path.exists(lrc_path):
        progress.stop()
        if lyrics_mode.startswith("📺 3"):
            msg = f"[bold yellow]⚠️ Lirik dilewati: Video YouTube tidak memiliki CC untuk {title[:30]}...[/bold yellow]"
        else:
            msg = f"[bold yellow]⚠️ Lirik dilewati: Tidak ditemukan di database lirik untuk {title[:30]}...[/bold yellow]"
        console.print(msg)
        progress.start()"""

code = code.replace(old_logic, new_logic)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
