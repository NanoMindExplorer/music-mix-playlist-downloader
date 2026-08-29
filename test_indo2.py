from mmpd.lyrics_providers import build_default_chain
from mmpd.types import TrackInfo
chain = build_default_chain()
track = TrackInfo(title="Sempurna - Andra and The BackBone")
result = chain.search(track)
if result:
    print(f"FOUND via {result.provider}")
else:
    print("NOT FOUND")
