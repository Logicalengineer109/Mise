# This is request module of this project
from request import Request
from auth import headers
import json

class BusinessSearch:
    def __init__(self, term, location, price=None):
        self._param = {'term' : term, 'location' : location}
        if price:
            self._param['price'] = price
        self._base_url = 'https://api.yelp.com/v3/businesses/search'
        self._business_list = self._search_business()

    def _search_business(self):
        business_search_request = Request.get_content(url=self._base_url, param=self._param)
        return business_search_request['businesses'] if business_search_request is not None else []

    def _parse_results(self, data):
        # Categories data : 'categories': [{'alias': 'bakeries', 'title': 'Bakeries'}]
        categories = ' '.join([category['title'] for category in data.get('categories', [])])

        # Longitude and latitude data :  'coordinates': {'latitude': 45.5232, 'longitude': -73.583459}
        # 'NULL' keeps the unquoted lat/long slots in the INSERT valid when Yelp omits them.
        coordinates = data.get('coordinates') or {}
        longitude = coordinates.get('longitude', 'NULL')
        latitude = coordinates.get('latitude', 'NULL')
        longitude = 'NULL' if longitude is None else longitude
        latitude = 'NULL' if latitude is None else latitude

        # Location example : 'location': { 'display_address': ['316 Avenue du Mont-Royal E', 'Montreal, QC H2T 1P7', 'Canada']}
        location = ','.join((data.get('location') or {}).get('display_address', []))

        # Yelp omits optional fields (price, phone, coordinates) for many businesses.
        return {"id" : data['id'], "name" : self._add_escape_character(data['name']), "image_url" : data.get('image_url', ''), "url" : data.get('url', ''),
                "review_count" : data.get('review_count', 0), "categories" : categories, "rating" : data.get('rating', 0),
                "latitude" : latitude, "longitude" : longitude, "price" : data.get('price', ''), "location" : self._add_escape_character(location),
                "display_phone" : data.get('display_phone', '')
                }

    def _add_escape_character(self, data):
        return data.replace("'", "''")

    def get_results(self):
        return [self._parse_results(business) for business in self._business_list]