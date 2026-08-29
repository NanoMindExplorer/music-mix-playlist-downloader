with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

old_block = """    if not temp_cover_glob:
        return

    cover_path = temp_cover_glob[0]
    temp_audio = os.path.join(dir_path, f"temp_{filename}")"""

new_block = """    from mmpd.cover_providers import download_cover_art
    from mmpd.utils.ffmpeg import crop_cover_to_square
    
    temp_api_cover = os.path.join(dir_path, f"api_cover_{title}.jpg")
    cover_path = None
    
    if download_cover_art(title, "", temp_api_cover):
        cover_path = temp_api_cover
    elif temp_cover_glob:
        yt_cover = temp_cover_glob[0]
        temp_crop_cover = os.path.join(dir_path, f"cropped_{title}.jpg")
        if crop_cover_to_square(yt_cover, temp_crop_cover):
            cover_path = temp_crop_cover
        else:
            cover_path = yt_cover
            
    if not cover_path:
        return

    temp_audio = os.path.join(dir_path, f"temp_{filename}")"""

code = code.replace(old_block, new_block)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
