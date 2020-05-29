import unittest
from unittest import mock

from lib.rest_endpoint.rest_deprecation_handler import RestDeprecationHandler


class TestRestDeprecationHandler(unittest.TestCase):

    sample_package = "vcenter"
    sample_service = "com.vmware.vcenter"
    sample_operation = "list"
    sample_method = "get"
    sample_path = "/rest/vcenter/vm"
    replacement_dict = {sample_service: {sample_operation: (sample_method, sample_path)}}
    rest_deprecation_handler = RestDeprecationHandler(replacement_dict)

    def test_rest_deprecation(self):
        path_obj = {"operationId": self.sample_operation, "method": self.sample_method}
        self.rest_deprecation_handler.add_deprecation_information(path_obj, self.sample_package, self.sample_service)

        self.assertEqual(path_obj['deprecated'], True)
        self.assertEqual(path_obj["x-vmw-deprecated"]["replacement"], "api_vcenter.json#/paths/~1rest~1vcenter~1vm/get")


if __name__ == '__main__':
    unittest.main()
