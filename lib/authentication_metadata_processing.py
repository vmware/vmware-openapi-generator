import six


def get_authentication_dict(auth_component_svc):
    auth_dict = {}
    auth_components = auth_component_svc.list()
    for auth_component in auth_components:
        auth_component_data = auth_component_svc.get(auth_component)
        for package_name, package_info in six.iteritems(auth_component_data.info.packages):
            if package_name in auth_dict:
                auth_dict[package_name]


def get_operation_scheme_top_level(auth_dict, package_name, service_name, operation_name):
    pass


def get_operation_scheme_package_level(auth_component, service_name, operation_name):
    pass


def get_operation_scheme_service_level(auth_component, operation_name):
    pass


def get_operation_scheme(auth_component):
    pass


class AuthenticationComponentBuilder:

    @staticmethod
    def build_package_level_component(package_info):
        package_component = AuthenticationComponent()
        package_component.add_schemes(AuthenticationComponentBuilder.__extract_schemes_list(package_info))
        for service_name, service_info in six.iteritems(package_info.services):
            service_component = AuthenticationComponentBuilder.build_service_level_component(service_info)
            package_component.add_subcomponent(service_component, service_name)
        return package_component

    @staticmethod
    def build_service_level_component(service_info):
        service_component = AuthenticationComponent()
        service_component.add_schemes(AuthenticationComponentBuilder.__extract_schemes_list(service_info))
        for operation_name, operation_info in six.iteritems(service_info.operations):
            operation_component = AuthenticationComponentBuilder.build_operation_level_component(operation_info)
            service_component.add_subcomponent(operation_component, operation_name)
        return service_component

    @staticmethod
    def build_operation_level_component(operation_info):
        operation_component = AuthenticationComponent()
        operation_component.add_schemes(AuthenticationComponentBuilder.__extract_schemes_list(operation_info))
        return operation_component

    @staticmethod
    def __extract_schemes_list(auth_component):
        return [auth_info.scheme for auth_info in auth_component.schemes]


class AuthenticationComponent:

    def __init__(self):
        self.scheme_set = set()
        self.subcomponents_dict = {}

    def add_schemes(self, schemes_iterable):
        self.scheme_set.update(schemes_iterable)

    def get_schemes(self):
        return self.scheme_set

    def get_subcomponents(self):
        return self.subcomponents_dict

    def add_subcomponent(self, added_auth_component, auth_component_name):
        if auth_component_name not in self.subcomponents_dict:
            self.subcomponents_dict[auth_component_name] = added_auth_component
        else:
            existing_component = self.subcomponents_dict[auth_component_name]
            existing_component.add_schemes(added_auth_component.get_schemes())
            for name_added_subcomponent, added_subcomponent in six.iteritems(added_auth_component.get_subcomponents()):
                existing_component.add_subcomponent(added_subcomponent, name_added_subcomponent)






