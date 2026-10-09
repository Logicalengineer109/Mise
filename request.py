import  requests
from auth import headers
import json

class Request:
    def __init__(self):
        self._header = headers

    @staticmethod
    def get_content(url, param):
        response = requests.get(url, headers=headers, params=param)
        if response.status_code == 200:
            return json.loads(response.content)
        else:
            print(f"Request completed with Error. Response Code : {response.status_code}")
            try:
                error = response.json().get('error', {})
                print(f"  {error.get('code', '')}: {error.get('description', response.text[:200])}")
                if error.get('field') == 'Authorization':
                    print("  -> Set a valid 128-character Yelp Fusion API_KEY in config.cfg")
            except ValueError:
                print(f"  {response.text[:200]}")
            return None