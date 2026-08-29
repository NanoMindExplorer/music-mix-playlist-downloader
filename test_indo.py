from mmpd.lyrics_providers import build_default_chain
from mmpd.types import TrackInfo
chain = build_default_chain()
track = TrackInfo(title="Sempurna", artist="Andra and The BackBone")
result = chain.search(track)
if result:
    print(f"FOUND via {result.provider}: {result.best_lyrics[:100]}")
else:
    print("NOT FOUND")
