import requests
import re

def get_official_title(query):
    try:
        # Hapus kata-kata sampah umum
        query = re.sub(r'(?i)(official|music video|mv|lyric|video|audio|cover)', '', query)
        res = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=1").json()
        if res['resultCount'] > 0:
            track = res['results'][0]['trackName']
            artist = res['results'][0]['artistName']
            return f"{artist} {track}"
    except:
        pass
    return None

print(get_official_title("seven oops lovers"))
print(get_official_title("LiSA - Gurenge (Official Music Video)"))
print(get_official_title("Naruto Shippuden OP 9 Lovers"))
