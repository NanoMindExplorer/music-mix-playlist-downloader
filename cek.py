import sys
sys.path.insert(0, '.')
from mmpd.spotify import build_ytsearch_query
q = build_ytsearch_query('Test Song', limit=1)
print(f'Query: {q}')
has_filter = '-instrumental' in q
print(f'Filter aktif: {has_filter}')
