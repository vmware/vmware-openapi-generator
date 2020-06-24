import unittest

from lib.authentication_metadata_processing import AuthenticationComponent


class TestAuthenticationComponent(unittest.TestCase):

    def test_authentication_component_operations(self):
        package_level_auth_component = AuthenticationComponent()
        package_level_auth_component.add_schemes(["basic_auth"])

        expected_scheme = {"basic_auth"}
        self.assertEqual(package_level_auth_component.get_schemes(), expected_scheme)

        service_level_auth_component = AuthenticationComponent()
        service_level_auth_component.add_schemes(["token"])
        package_level_auth_component.add_authentication_component(service_level_auth_component, "my.token.auth.service")

        subcomponents_dict = package_level_auth_component.get_subcomponents()
        expected_subcomponent_scheme = {"token"}
        self.assertEqual(subcomponents_dict.get("my.token.auth.service").get_schemes(), expected_subcomponent_scheme)
        
        operation_level_auth_component = AuthenticationComponent()
        operation_level_auth_component.add_schemes(["saml_token"])
        service_level_auth_component_updated = AuthenticationComponent()
        service_level_auth_component_updated.add_schemes({"token", "oauth2"})
        service_level_auth_component_updated.add_authentication_component(operation_level_auth_component,
                                                                          "my.token.auth.service.list")
        package_level_auth_component.add_authentication_component(service_level_auth_component_updated,
                                                                  "my.token.auth.service")

        expected_subcomponent_scheme = {"token", "oauth2"}
        self.assertEqual(subcomponents_dict.get("my.token.auth.service").get_schemes(), expected_subcomponent_scheme)

        operation_level_auth_component_updated = AuthenticationComponent()
        operation_level_auth_component_updated.add_schemes(["session_id"])
        service_level_auth_component_updated.add_authentication_component(operation_level_auth_component_updated,
                                                                          "my.token.auth.service.list")
        service_level_auth_component_updated.add_authentication_component(operation_level_auth_component_updated,
                                                                          "my.token.auth.service.create")
        package_level_auth_component.add_authentication_component(service_level_auth_component_updated,
                                                                  "my.token.auth.service")

        subcomponents_dict = package_level_auth_component.get_subcomponents()
        operation_level_subcomponents_dict = subcomponents_dict.get("my.token.auth.service").get_subcomponents()
        self.assertEqual(len(operation_level_subcomponents_dict), 2)

        self.assertEqual(operation_level_subcomponents_dict.get("my.token.auth.service.list").get_schemes(),
                         {"session_id", "saml_token"})
        self.assertEqual(operation_level_subcomponents_dict.get("my.token.auth.service.create").get_schemes(),
                         {"session_id"})



if __name__ == '__main__':
    unittest.main()
