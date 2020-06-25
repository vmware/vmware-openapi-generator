import six


def get_authentication_dict(auth_component_svc):
    auth_dict = {}
    auth_components = auth_component_svc.list()
    for auth_component in auth_components:
        auth_component_data = auth_component_svc.get(auth_component)
        for package_name, package_info in six.iteritems(auth_component_data.info.packages):
            if package_name not in auth_dict:
                auth_dict[package_name] = AuthenticationComponentBuilder.build_package_level_component(package_info)
            else:
                new_package_component = AuthenticationComponentBuilder.build_package_level_component(package_info)
                existing_package_component = auth_dict[package_name]
                for service_name, service_info in six.iteritems(new_package_component.get_subcomponents_dict()):
                    existing_package_component.add_subcomponent(service_info, service_name)
    return auth_dict


class AuthenticationDictNavigator:

    def __init__(self, auth_dict):
        self.auth_dict = auth_dict

    def find_schemes_list(self, operation_id, service_name, package):
        component = self.__depth_first_search_component(service_name, package)
        if component is not None:
            operation_component = component.get_subcomponents_dict().get(operation_id)
            if operation_component is not None:
                return operation_component.get_schemes_list()
            else:
                return component.get_schemes_list()

        service_name = ".".join(service_name.split('.')[-1])
        while service_name:
            component = self.__depth_first_search_component(service_name, package)
            if component is not None:
                return component.get_schemes_list()
            else:
                service_name = ".".join(service_name.split('.')[-1])

        return None


    def __depth_first_search_component(self, service_name, package):
        if service_name in self.auth_dict:
            return self.auth_dict[service_name]
        else:
            for package_name, package_component in six.iteritems(self.auth_dict):
                if package not in package_name:
                    continue

                component = package_component.recursive_search_for_component(service_name)
                if component is not None:
                    return component

        return None



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

    def get_schemes_set(self):
        return self.scheme_set

    def get_subcomponents_dict(self):
        return self.subcomponents_dict

    def add_subcomponent(self, added_auth_component, auth_component_name):
        if auth_component_name not in self.subcomponents_dict:
            self.subcomponents_dict[auth_component_name] = added_auth_component
        else:
            existing_component = self.subcomponents_dict[auth_component_name]
            existing_component.add_schemes(added_auth_component.get_schemes_set())
            for name_added_subcomponent, added_subcomponent in six.iteritems(added_auth_component.get_subcomponents_dict()):
                existing_component.add_subcomponent(added_subcomponent, name_added_subcomponent)

    def recursive_search_for_component(self, component_name):
        if self.subcomponents_dict == {}:
            return None
        elif component_name in self.subcomponents_dict:
            return self.subcomponents_dict[component_name]
        else:
            for _, subcomponent in six.iteritems(self.subcomponents_dict):
                return subcomponent.recursive_search_for_component(component_name)
