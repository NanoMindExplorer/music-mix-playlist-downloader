def fix_file(filepath):
    with open(filepath, "r") as f:
        code = f.read()
    
    # We want to remove the specific 'import os' inside the if block.
    # We'll just replace '                import os\n                os.environ' with '                os.environ'
    code = code.replace('                import os\n                os.environ', '                os.environ')
    
    with open(filepath, "w") as f:
        f.write(code)

fix_file("mmpd/modes/download.py")
fix_file("mmpd/modes/retrofit.py")
