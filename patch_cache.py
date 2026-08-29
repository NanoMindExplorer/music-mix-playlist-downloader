with open("mmpd/cache.py", "r") as f:
    code = f.read()

new_logic = """_DB_INITIALIZED = False

def _get_connection() -> sqlite3.Connection:
    \"\"\"Buka koneksi SQLite + init tabel (sekali per process).\"\"\"
    global _DB_INITIALIZED
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    
    with _LOCK:
        if not _DB_INITIALIZED:
            _init_db(conn)
            _DB_INITIALIZED = True
            
    return conn"""

old_logic = """def _get_connection() -> sqlite3.Connection:
    \"\"\"Buka koneksi SQLite + init tabel.\"\"\"
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=30.0)  # 30s timeout untuk lock
    _init_db(conn)
    return conn"""

code = code.replace(old_logic, new_logic)
with open("mmpd/cache.py", "w") as f:
    f.write(code)
