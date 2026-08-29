from mmpd.lyrics_providers import LrclibProvider
from mmpd.types import TrackInfo
provider = LrclibProvider()
print("Search 1:", provider.search(TrackInfo(title="Armada_-_Asal_Kau_Bahagia")) is not None)
