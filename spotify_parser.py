import re
import json
import urllib.request

def parse_spotify_url(url):
    # Support for open.spotify.com
    if "open.spotify.com" not in url:
        return []
    
    # Change /track/ or /playlist/ to embed URL
    embed_url = url.replace("open.spotify.com", "open.spotify.com/embed").split("?")[0]
    
    req = urllib.request.Request(embed_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching Spotify: {e}")
        return []
        
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not m:
        print("Could not find Spotify data.")
        return []
        
    try:
        data = json.loads(m.group(1))
        entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
        
        results = []
        # If it's a playlist or album
        if 'trackList' in entity:
            for item in entity['trackList']:
                if 'title' in item and 'subtitle' in item:
                    results.append(f"{item['title']} {item['subtitle']}")
        # If it's a single track
        elif 'title' in entity and 'subtitle' in entity:
            results.append(f"{entity['title']} {entity['subtitle']}")
            
        return results
    except Exception as e:
        print(f"Error parsing Spotify data: {e}")
        return []

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(parse_spotify_url(sys.argv[1]))
