from mmpd.lyrics_providers import LrclibProvider
from mmpd.types import TrackInfo
provider = LrclibProvider()
print("Search Lirik:", provider.search(TrackInfo(title="Armada - Asal Kau Bahagia Lirik")) is not None)
print("Search Lirik Video:", provider.search(TrackInfo(title="Armada - Asal Kau Bahagia Lirik Video")) is not None)
print("Search Lirik Lagu:", provider.search(TrackInfo(title="Armada - Asal Kau Bahagia Lirik Lagu")) is not None)
print("Search Lirik Dan Chord:", provider.search(TrackInfo(title="Armada - Asal Kau Bahagia Lirik Dan Chord")) is not None)
print("Search Lirik Karaoke:", provider.search(TrackInfo(title="Armada - Asal Kau Bahagia Karaoke")) is not None)
