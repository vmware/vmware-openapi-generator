import unittest
from unittest import mock

from lib.rest_endpoint.rest_deprecation_handler import RestDeprecationHandler


class TestRestDeprecationHandler(unittest.TestCase):

    sample_package = "vsphere"
    sample_service = "com.test.service"
    sample_operation = "list"
    sample_method = "get"
    sample_path = "/com/test/sample/list"
    replacement_map = {sample_service: {sample_operation: {sample_method: sample_path}}}
    rest_deprecation_handler = RestDeprecationHandler(replacement_map)

    def test_rest_deprecation(self):
        path_obj = {"operationId": self.sample_operation, "method": self.sample_method}
        self.rest_deprecation_handler.add_deprecation_information(path_obj, self.sample_package, self.sample_service)

        self.assertEqual(path_obj['deprecated'], True)
        self.assertEqual(path_obj["x-vmw-deprecated"]["replacement"], "api_vsphere.json#/paths/~1com~1test~1sample~1list/get")


if __name__ == '__main__':
    unittest.main()
