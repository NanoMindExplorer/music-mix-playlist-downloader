from mmpd.lyrics_providers import build_default_chain
from mmpd.types import TrackInfo
import logging

logging.basicConfig(level=logging.DEBUG)

chain = build_default_chain("Dewa 19 Kangen")
res = chain.search(TrackInfo("Dewa 19 Kangen"))
if res:
    print("Found via", res.provider)
else:
    print("Not found")
