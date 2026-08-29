with open("tests/test_spotify.py", "r") as f:
    code = f.read()

old_logic = """    def test_basic_query(self):
        \"\"\"Test basic ytsearch query dengan instrumental filter.\"\"\"
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Adele Hello", limit=1)
        assert result.startswith("ytsearch1:Adele Hello")
        assert 'official audio' in result

    def test_query_with_limit_3(self):
        \"\"\"Test query dengan limit 3.\"\"\"
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Test Song", limit=3)"""

new_logic = """    def test_basic_query(self):
        \"\"\"Test basic ytsearch query dengan instrumental filter.\"\"\"
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Adele Hello", limit=1)
        assert result.startswith("ytsearch1:Adele Hello")
        assert '-instrumental' in result
        assert '-karaoke' in result

    def test_query_with_limit_3(self):
        \"\"\"Test query dengan limit 3.\"\"\"
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Test Song", limit=3)
        assert result.startswith("ytsearch3:Test Song")
        assert '-instrumental' in result"""

code = code.replace(old_logic, new_logic)
with open("tests/test_spotify.py", "w") as f:
    f.write(code)
