import syncedlyrics
# Try a less famous Indonesian song
print("Test 1:", syncedlyrics.search("Hindia - Evaluasi") is not None)
print("Test 2:", syncedlyrics.search("Evaluasi Hindia") is not None)
