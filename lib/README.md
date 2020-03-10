# lib/readme.md
Here the documentation for the .py files in the lib folder namely ```establish_connection.py```, ```dictionary_processing.py```, ```path_processing.py```, ```url_processing.py```, ```type_handler_common.py``` and ```utils.py``` is covered. We will go through them in order of their usage in the main function. All these have been imported and used as per their requirement.
## Part : 1
The ```get_input_params()``` function of the establish_connection.py is used to get the input parameters from the command line. The argument parser object holds all the information required to parse the command line arguments into python objects. 

It takes the following parameters as inputs:
1. **metadata-url** : It is the url of the metadata API. If IP address of the vCenter (vcip) is provided, it takes in the values as **https://< vcip >/api**
2. **rest-navigation-url** : This is the url for rest navigation. If vcip is provided this url becomes **https://< vcip >/rest**
3. **vcip** : It is the IP Address of the vCenter server. It is used to specify the metadata-url and rest-navigation-url.
4. **output** : This is output directory where the generated swagger or openapi files will be stored. If the output directory is not supplied, the present working directory is chosen as the output directory.
5. **tag-seperator** : It is the seperator to be used in tag names i.e. '/'.
6. **insecure** : It is used to check the SSL certificate validation. If this parameter is supplied as an input argument, it bypasses the certificate validation. If not passed, the program will check for validation.
7. **unique-operation-ids** : This parameter is passed to generate unique ids for all operation/functions. Default value of this parameter is false. A required semantic rule of the open api specification is that the operations should have a unique operation name even if they are under different paths. If this parameter is ignored the generated swagger file may throw semantic error if it fails the openapi validation.
8. **metamodel-components** : If this parameter is passed, then each metamodel component retreived from the vCenter server is saved in a different .json file under the metamodel directory.
9. **host** : It is the IP Address of the host that serves the API. By default the value is < vcenter >
10. **enable-filtering** : It is used to filter out internal and unrealeased API's so that if service info of the API is still under modification, it is skipped for processing.
11. **oas** : This parameter is used to specify as to which version of swagger file the user wants to generate. By default the generated files are of version 3 i.e openapi. If the user wants to generate the version 2 files, the parameter needs to be passed explicitly. 

After processing the input parameters passed by the user, Part 1 declares some dictionary data structures such as enumeration_dict{}, structure_dict{}, service_dict{} and service_urls_map{} which are used to store and process the data retrived from the metamodel components, services, packages and enumerations.

## Part : 2
The python ```timeit``` library is used to measure the execution of code snippets and it's function ```default_timer()``` fetches the current system time. We use the urllib's connection pooling to create a session object which allows us to persist certain parameters across http requests. The ```get_request_connector()``` is a python automation SDK function to establish connection with the vAPI provider. This function takes in the session object and metadata url as the arguments and returns the connector object. In vCenter, the vAPI provider is a process which converts the vModel specification files to the metamodel and provides them in a format specific to the message protocol which is json here in our case. The vAPI provider is accessed through json RPC and it hits the /api endpoint, hence we require the metadata url. If filtering has been enabled, the ```ApplicationContext``` object is used to filter out the internal and unreleased api's. 
``` python
def get_component_service(connector):
    stub_config = StubConfigurationFactory.new_std_configuration(connector)
    component_svc = metamodel_client.Component(stub_config)
    return component_svc
```
In the ```get_component_service()``` function defined inside the lib/utils.py file as above, the stub configuration factory class takes in the connector object in order to create a stub configuration object with all the standard errors registered. This object acts as the configuration data object for  the vAPI stub classes. Further, the ```Component()``` method of the ```metamodel_client``` class takes in this stub configuration object to create a ```component_svc``` object which is used to retrive the metamodel information of the component elements. A component is nothing but a set of functionalities deployed and versioned together just like all the libraries that are a part of VMware content library is covered under one component. 

## Part : 3
```python
def populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, base_url, generate_metamodel):
    components = component_svc.list()
    for component in components:
        component_data = component_svc.get(component)
        if generate_metamodel:
            if not os.path.exists('metamodel'):
                os.mkdir('metamodel')
            utils.write_json_data_to_file('metamodel/'+component+'.json', objectTodict(component_data))
        component_packages = component_data.info.packages
        for package in component_packages:
            package_info = component_packages.get(package)
            for enumeration, enumeration_info in package_info.enumerations.items():
                enumeration_dict[enumeration] = enumeration_info
            for structure, structure_info in package_info.structures.items():
                structure_dict[structure] = structure_info
                for enum_name, enum_info in structure_info.enumerations.items():
                    enumeration_dict[enum_name] = enum_info
            for service, service_info in package_info.services.items():
                service_dict[service] = service_info
                service_urls_map[get_service_url_from_service_id(base_url, service)] = service
                for structure_name, structure_info in service_info.structures.items():
                    structure_dict[structure_name] = structure_info
                    for et1, et_info1 in structure_info.enumerations.items():
                        enumeration_dict[et1] = et_info1
                for enum_name, enum_info in service_info.enumerations.items():
                    enumeration_dict[enum_name] = enum_info
```
The ```populate_dicts()``` function of the ```lib/dictionary_processing.py``` file fills the data structures that we declared in Part 1. The identifiers of all the component elements present in the component_svc object are listed in the ```components``` list. By looping through this list, the ```component_svc.get()``` function retrieves the metamodel information of the component's elements in a ```component_data``` object. Here, if the input parameter **generate_metamodel** is set to True, the metamodel information of each component is written inside a different file in a json format under the metamodel directory. The metamodel information follows a hierarchy structure, consisting of the components at the top. Each component contains metadata of the packages. Each package consists of enumerations, structures and services metadata and a service is further composed of structure and enumeration metadata. This heirarchy structure is followed while iterating the component elements and while filling the dictionaries. The key of each of the dictionaries specifies the name of the element and the value part specifies that element's metamodel information.

```python
def get_service_urls_from_rest_navigation(rest_navigation_url, verify):
    component_services_urls = get_component_services_urls(rest_navigation_url, verify)
    return get_all_services_urls(component_services_urls, verify)

def get_component_services_urls(cloudvm_url, verify):
    components_url = utils.get_json(cloudvm_url, verify)['components']['href']
    components = utils.get_json(components_url, verify)
    return [component['services']['href'] for component in components]

def get_all_services_urls(components_urls, verify):
    service_url_dict = {}
    for url in components_urls:
        services = utils.get_json(url, verify)
        for service in services:
            service_url_dict[service['href']] = service['name']
    return service_url_dict
```

The ```service_urls_map``` is populated using the function calls in ```get_service_urls_from_rest_navigation()``` function. This function extracts the urls of the services using the rest navigation url but since these services are inside the components, the url of the component needs to be known first. In order to extract the url of the components, the ```get_component_services_url()``` method is used. It takes in the rest navigation url, makes a request at the /rest endpoint using the requests.get method of the ```get_json()```. This returns a json responses with two main attributes, **components** and **resources**. Each of these attributes, contains a key-value pair where the key is **href** and value contains the **url** from where we can get a list of all the components/resources. An example for components attribute is **[ href: https://< vCenter ip >/rest/com/vmware/vapi/rest/navigation/component ]** and resources attribute is **[ href: https://< vCenter ip >/rest/com/vmware/vapi/rest/navigation/resources ]**. The component url is further used by the ```get_component_services_url()```to extract the urls of all the components inside it. We iterate over these urls one by one to get the list of all the service urls supported by each component url. Finally the ```get_all_services_urls()``` populates the service_urls_map. It gets the service url and fills the dict by putting key as the url link ( with base template as **https://< vCenter ip >/rest/com/vmware/< package name >/< service path >** ) and value as the service name i.e { link : service_name }. 

```build_error_map()``` of the ```lib/utils.py``` constructs an error dictionary that maps the vAPI errors corresponding to their HTTP status codes.

```add_service_urls_using_metamodel()``` of the ```lib/dictionary_processing.py``` is used to extract and differentiate the packages which have /api and /rest as their endpoint. The ones with /api as their endpoint are put under the ```package_dict_api{}``` dictionary and ones with /rest are under ```package_dict{}```.
```python
def add_service_urls_using_metamodel(service_urls_map, service_dict, rest_navigation_url):

    package_dict_api = {}
    package_dict = {}

    all_rest_services = []
    for i in service_urls_map:
        all_rest_services.append(service_urls_map[i][0])

    rest_services = {}
    for k, v in service_urls_map.items():
        rest_services.update({
            v:k
        })


    for service in service_dict:
        # if service not in all_rest_services:
        check, path_list = get_paths_inside_metamodel( service, service_dict )
        if check:
            for path in path_list:
                service_urls_map[path] = (service, '/api')
                package_name = path.split('/')[1]
                pack_arr = package_dict_api.get(package_name, [])
                if pack_arr == []:
                    package_dict_api[package_name] = pack_arr
                pack_arr.append(path)
        else:
            service_url = rest_services.get(service, None)
            if service_url != None:
                service_path = get_service_path_from_service_url(service_url, rest_navigation_url)
                service_urls_map[service_path] = (service, '/rest')
                package = service_path.split('/')[3]
                if package in package_dict:
                    packages = package_dict[package]
                    packages.append(service_path)
                else:
                    package_dict.setdefault(package, [service_path])
            else:
                print("Service doesnot belong to either /api or /rest ", service)
    return package_dict_api, package_dict

def get_paths_inside_metamodel(service, service_dict):
    path_list = set()
    for operation_id in service_dict[service].operations.keys():
        for request in service_dict[service].operations[operation_id].metadata.keys():
            if request.lower() in ('post', 'put', 'patch', 'get', 'delete'):
                path_list.add(service_dict[service].operations[operation_id].metadata[request].elements['path'].string_value)
    
    if path_list == set():
        return False, []

    return True, sorted(list(path_list))
```
```add_service_urls_using_metamodel()``` method iterates over the services in ```service_dict{}``` and calls ```get_paths_inside_metamodel()``` to check if the metadata of the service contains http operations like post, put, patch, get and delete. If the service metadata contains these, it's corresponding package name is extracted and used to populate the package_dict_api. So package_dict_api contains keys with package name and value as a list of services urls supported by that package where each entry of the list is a pair of service url and "/api" string. If service metadata does not contain the http operations, the package_dict gets populated with key as package name and value as a list of service urls where each entry of the list is a pair of service url and "/rest" string to signify the endpint. Hence, these dictionaries look like { package_name : [(service_url, /api)]}