from lib import utils

class RestNavigationHandler:

    def __init__(self, rest_navigation_url):
        self.rest_navigation_url = rest_navigation_url

    def get_service_operations(self, service_url):
        return utils.get_json(self.rest_navigation_url + service_url + '?~method=OPTIONS', False)

    def get_rest_navigation_url(self):
        return self.rest_navigation_url
