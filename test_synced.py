import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Monkey patch requests.Session to force a 30-second timeout
_original_request = requests.Session.request
def _patched_request(self, method, url, **kwargs):
    kwargs["timeout"] = 30
    return _original_request(self, method, url, **kwargs)
requests.Session.request = _patched_request

import syncedlyrics
print(syncedlyrics.search('Rainych JUSTadICE'))
