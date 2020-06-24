import six


def get_authentication_dict(auth_component_svc):
    auth_dict = {}
    auth_components = auth_component_svc.list()
    for auth_component in auth_components:
        auth_component_data = auth_component_svc.get(auth_component)
        for package_name, package_info in six.iteritems(auth_component_data.info.packages):
            if package_name in auth_dict:
                auth_dict[package_name]


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

    def add_authentication_component(self, added_auth_component, auth_component_name):
        if auth_component_name not in self.subcomponents_dict:
            self.subcomponents_dict[auth_component_name] = added_auth_component
        else:
            existing_component = self.subcomponents_dict[auth_component_name]
            existing_component.add_schemes(added_auth_component.get_schemes())
            for name_added_subcomponent, added_subcomponent in six.iteritems(added_auth_component.get_subcomponents()):
                existing_component.add_authentication_component(added_subcomponent, name_added_subcomponent)

    #def get_






