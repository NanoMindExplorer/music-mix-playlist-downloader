with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

old_logic = """                elif lang == "th":
                    anyascii = _get_anyascii()
                    new_text = anyascii(text)
                    return f"{time_tags}{new_text}\\n"
            except Exception as e:"""

new_logic = """                elif lang == "yue":
                    import ToJyutping
                    new_text = ToJyutping.get_jyutping_text(text)
                    return f"{time_tags}{new_text}\\n"
                elif lang == "th":
                    from pythainlp.transliterate import romanize
                    new_text = romanize(text, engine="royin")
                    return f"{time_tags}{new_text}\\n"
            except Exception as e:"""

code = code.replace(old_logic, new_logic)
with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
