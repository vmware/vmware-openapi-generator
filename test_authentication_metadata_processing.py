import unittest

from lib.authentication_metadata_processing import AuthenticationComponent, AuthenticationDictNavigator
from lib.authentication_metadata_processing import AuthenticationComponentBuilder
from unittest import mock

class TestAuthenticationComponent(unittest.TestCase):

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

    def test_authentication_component(self):
        package_level_auth_component = AuthenticationComponent()
        package_level_auth_component.add_schemes(["basic_auth"])

        self.assertEqual({"basic_auth"}, package_level_auth_component.get_schemes_set())

        service_level_auth_component = AuthenticationComponent()
        service_level_auth_component.add_schemes(["token"])
        package_level_auth_component.add_subcomponent(service_level_auth_component, "my.token.auth.service")

        subcomponents_dict = package_level_auth_component.get_subcomponents_dict()
        self.assertEqual({"token"}, subcomponents_dict.get("my.token.auth.service").get_schemes_set())
        
        operation_level_auth_component = AuthenticationComponent()
        operation_level_auth_component.add_schemes(["saml_token"])
        service_level_auth_component_updated = AuthenticationComponent()
        service_level_auth_component_updated.add_schemes({"token", "oauth2"})
        service_level_auth_component_updated.add_subcomponent(operation_level_auth_component,
                                                                          "my.token.auth.service.list")
        package_level_auth_component.add_subcomponent(service_level_auth_component_updated,
                                                                  "my.token.auth.service")

        self.assertEqual({"token", "oauth2"}, subcomponents_dict.get("my.token.auth.service").get_schemes_set())

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
        self.assertEqual(2, len(operation_level_subcomponents_dict))

        self.assertEqual({"session_id", "saml_token"},
                         operation_level_subcomponents_dict.get("my.token.auth.service.list").get_schemes_set())
        self.assertEqual({"session_id"},
                         operation_level_subcomponents_dict.get("my.token.auth.service.create").get_schemes_set())


        found_component = package_level_auth_component.recursive_search_for_component("my.token.auth.service.list")
        self.assertEqual({"session_id", "saml_token"}, found_component.get_schemes_set())
        found_component = package_level_auth_component.recursive_search_for_component("my.token.auth.service")
        self.assertEqual({"token", "oauth2"}, found_component.get_schemes_set())


    def test_authentication_component_builder(self):
        package_component = AuthenticationComponentBuilder.build_package_level_component(self.package_info_mock)
        self.assertEqual({"oauth", "session_id"}, package_component.get_schemes_set())
        service_component = package_component.get_subcomponents_dict()["com.vmware.cis.session"]
        self.assertEqual({"oauth", "token"}, service_component.get_schemes_set())
        operation_component = service_component.get_subcomponents_dict()["create"]
        self.assertEqual({"session_id", "token"}, operation_component.get_schemes_set())


    def test_authentication_dict_navigator(self):
        package_component = AuthenticationComponentBuilder.build_package_level_component(self.package_info_mock)
        auth_dict = {"com.vmware.cis": package_component}
        navigator = AuthenticationDictNavigator(auth_dict)

        # 1. Existing package, existing service, existing operation
        self.assertEqual({"session_id", "token"}, navigator.find_schemes_set("create", "com.vmware.cis.session", "cis"))

        # 2. Existing package, existing service, non-existing operation
        self.assertEqual({"oauth", "token"}, navigator.find_schemes_set("update", "com.vmware.cis.session", "cis"))

        # 3. Existing package, non-existing service
        self.assertEqual({"oauth", "session_id"}, navigator.find_schemes_set("update", "com.vmware.cis.tasks", "cis"))

        # 4. Service name equal to package name
        self.assertEqual({"oauth", "session_id"}, navigator.find_schemes_set("update", "com.vmware.cis", "cis"))

        # 5. Non-existing package
        self.assertEqual(None, navigator.find_schemes_set("update", "com.vmware.sample", "cis"))

if __name__ == '__main__':
    unittest.main()
