import requests

query = "Naruto Shippuden OP 9 - Lovers by 7!! (seven oops)"
res = requests.get(f"https://itunes.apple.com/search?term={query}&entity=song&limit=1").json()
if res['resultCount'] > 0:
    track = res['results'][0]['trackName']
    artist = res['results'][0]['artistName']
    print(f"FOUND: {artist} - {track}")
else:
    print("NOT FOUND")
