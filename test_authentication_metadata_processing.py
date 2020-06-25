import unittest

from lib.authentication_metadata_processing import AuthenticationComponent
from lib.authentication_metadata_processing import AuthenticationComponentBuilder
from unittest import mock

class TestAuthenticationComponent(unittest.TestCase):

    def test_authentication_component(self):
        package_level_auth_component = AuthenticationComponent()
        package_level_auth_component.add_schemes(["basic_auth"])

        expected_scheme = {"basic_auth"}
        self.assertEqual(package_level_auth_component.get_schemes_set(), expected_scheme)

        service_level_auth_component = AuthenticationComponent()
        service_level_auth_component.add_schemes(["token"])
        package_level_auth_component.add_subcomponent(service_level_auth_component, "my.token.auth.service")

        subcomponents_dict = package_level_auth_component.get_subcomponents_dict()
        expected_subcomponent_scheme = {"token"}
        self.assertEqual(subcomponents_dict.get("my.token.auth.service").get_schemes_set(), expected_subcomponent_scheme)
        
        operation_level_auth_component = AuthenticationComponent()
        operation_level_auth_component.add_schemes(["saml_token"])
        service_level_auth_component_updated = AuthenticationComponent()
        service_level_auth_component_updated.add_schemes({"token", "oauth2"})
        service_level_auth_component_updated.add_subcomponent(operation_level_auth_component,
                                                                          "my.token.auth.service.list")
        package_level_auth_component.add_subcomponent(service_level_auth_component_updated,
                                                                  "my.token.auth.service")

        expected_subcomponent_scheme = {"token", "oauth2"}
        self.assertEqual(subcomponents_dict.get("my.token.auth.service").get_schemes_set(), expected_subcomponent_scheme)

        operation_level_auth_component_updated = AuthenticationComponent()
        operation_level_auth_component_updated.add_schemes(["session_id"])
        service_level_auth_component_updated.add_subcomponent(operation_level_auth_component_updated,
                                                                          "my.token.auth.service.list")
        service_level_auth_component_updated.add_subcomponent(operation_level_auth_component_updated,
                                                                          "my.token.auth.service.create")
        package_level_auth_component.add_subcomponent(service_level_auth_component_updated,
                                                                  "my.token.auth.service")

        subcomponents_dict = package_level_auth_component.get_subcomponents_dict()
        operation_level_subcomponents_dict = subcomponents_dict.get("my.token.auth.service").get_subcomponents_dict()
        self.assertEqual(len(operation_level_subcomponents_dict), 2)

        self.assertEqual(operation_level_subcomponents_dict.get("my.token.auth.service.list").get_schemes_set(),
                         {"session_id", "saml_token"})
        self.assertEqual(operation_level_subcomponents_dict.get("my.token.auth.service.create").get_schemes_set(),
                         {"session_id"})


        found_component = package_level_auth_component.recursive_search_for_component("my.token.auth.service.list")
        self.assertEqual({"session_id", "saml_token"}, found_component.get_schemes_set())
        found_component = package_level_auth_component.recursive_search_for_component("my.token.auth.service")
        self.assertEqual({"token", "oauth2"}, found_component.get_schemes_set())


    def test_authentication_component_builder(self):
        session_id_auth_info_mock = mock.Mock()
        session_id_auth_info_mock.scheme = "session_id"
        token_auth_info_mock = mock.Mock()
        token_auth_info_mock.scheme = "token"
        oauth_auth_info_mock = mock.Mock()
        oauth_auth_info_mock.scheme = "oauth"
        operation_info_mock = mock.Mock()
        operation_info_mock.schemes = [session_id_auth_info_mock, token_auth_info_mock]
        service_info_mock = mock.Mock()
        service_info_mock.schemes = [token_auth_info_mock, oauth_auth_info_mock]
        service_info_mock.operations = {"create": operation_info_mock}
        package_info_mock = mock.Mock()
        package_info_mock.services = {"com.vmware.cis.session": service_info_mock}
        package_info_mock.schemes = [oauth_auth_info_mock, session_id_auth_info_mock]

        package_component = AuthenticationComponentBuilder.build_package_level_component(package_info_mock)
        expected_package_level_set = {"oauth", "session_id"}
        self.assertEqual(package_component.get_schemes_set(), expected_package_level_set)
        service_component = package_component.get_subcomponents_dict()["com.vmware.cis.session"]
        expected_schemes = {"oauth", "token"}
        self.assertEqual(service_component.get_schemes_set(), expected_schemes)
        operation_component = service_component.get_subcomponents_dict()["create"]
        expected_schemes = {"session_id", "token"}
        self.assertEqual(operation_component.get_schemes_set(), expected_schemes)

if __name__ == '__main__':
    unittest.main()
