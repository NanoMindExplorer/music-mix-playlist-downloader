import syncedlyrics
lrc = syncedlyrics.search("YOASOBI Idol", lang="id")
print("RESULT WITH lang='id':")
if lrc:
    print("\n".join(lrc.splitlines()[:15])) # print first 15 lines
else:
    print("None")
