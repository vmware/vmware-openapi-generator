# lib/api_endpoint/readme.md
The api_endpoint directory contains the ```api_url_processing.py``` file which provides functionality to process the /api endpoint specific urls and generate either openapi or swagger files depending upon the user requirement. The ```ApiUrlProcessing``` class encapuslates the functions specific to /api endpoint processing and inherits the ```UrlProcessing``` class defined inside the ```lib/url_processing.py``` which contains functionalities common to both /api and /rest endpoints. ```api_type_handler.py``` takes care of the structure and enumeration type processing for populating the ```type_dict{}``` of the ```process_service_urls()``` and inherits from ```lib/type_handler_common.py``` where type handling features common to /api and /rest have been taken care of. In ```api_metamodel2spec.py```, functions to get the path and process its http operations for /api endpoint api's are listed.

## Part : 5
This part makes use of multi-threading to process each **api endpoint package** inside ```package_dict_api``` independently as a thread and then join these threads together. ```process_service_urls()``` is the entry point function for processing the api service urls. It is called by creating an object of ```ApiUrlProcessing``` class. Since this function leads to a couple of other major function calls, let's try to get a hold of it in parts. It takes in service_urls of a package for each thread along with couple of other parameters which are processed one by one to deserialize the metadata they contain.
```python
def process_service_urls(
        self,
        package_name,
        service_urls,
        output_dir,
        structure_dict,
        enum_dict,
        service_dict,
        service_url_dict,
        error_map,
        rest_navigation_url,
        enable_filtering,
        spec,
        gen_unique_op_id):
    print('processing package ' + package_name + os.linesep)
    type_dict = {}
    path_list = []
    # PART : 5.1
    for service_url in service_urls:
        service_name, service_end_point = service_url_dict.get(
            service_url, None)
        service_info = service_dict.get(service_name, None)
        if service_info is None:
            continue
        if utils.is_filtered(service_info.metadata, enable_filtering):
            continue
    # PART : 5.1.1
        for operation_id, operation_info in service_info.operations.items():
            method, url = self.api_get_url_and_method(operation_info.metadata)

            # check for query parameters
            if 'params' in operation_info.metadata[method].elements:
                element_value = operation_info.metadata[method].elements['params']
                params = "&".join(element_value.list_value)
                url = url + '?' + params

                if spec == '2':
                    path = swagg.get_path(
                        operation_info,
                        method,
                        url,
                        service_name,
                        type_dict,
                        structure_dict,
                        enum_dict,
                        operation_id,
                        error_map,
                        enable_filtering)
                if spec == '3':
                    path = openapi.get_path(
                        operation_info,
                        method,
                        url,
                        service_name,
                        type_dict,
                        structure_dict,
                        enum_dict,
                        operation_id,
                        error_map,
                        enable_filtering)

                path_list.append(path)
        continue
    # PART : 5.2
    path_dict = self.convert_path_list_to_path_map(path_list)
    # PART : 5.3
    self.cleanup(path_dict=path_dict, type_dict=type_dict)
    if spec == '2':
        api_swagg_fpp.process_output(
            path_dict,
            type_dict,
            output_dir,
            package_name,
            gen_unique_op_id)
    if spec == '3':
        api_openapi_fpp.process_output(
            path_dict,
            type_dict,
            output_dir,
            package_name,
            gen_unique_op_id)
```
### Part : 5.1
We start iterating through api service urls corresponding to each package and get the service name from ```service_urls_dict{}``` for each service url. Using the service name, the metamodel information for each service is extracted from ```service_dict{}``` and stored as a ```service_info``` object. A ```service_info``` object contains the following attributes:
```
service_info {
    name:
    operations:
    structures:
    enumerations:
    constants:
    metadata:
    documentation:
    _extra_fields:
    _struct_value:
    _rest_convertor_mode: }
```
If service info object is none or its metadata contains keywords 'changing' or 'proposed', the service info is ignored for processing and we continue to the next service url.
# Part : 5.1.1
There are operations present inside a service_info object. We get the ```operation_id``` and ```operation_info``` from the items of a service_info's operations. The operation_info's metadata is checked for presence of http methods like put, post, patch, get and delete by ```api_get_url_and_method()``` which returns the http method and its corresponding url from metadata's elements. Also operation_info's metadata elements are checked for presence of parameters. If parameters are present they are prefixed with an '&' just like query parameters and attached as a suffix at the end of the url.```get_path()``` is the most important function which takes in operation info and constructs swagger based path specifications. Since path specifications and handling of parameters, responses is a bit different for swagger 2.0 and openapi, two copies of the function are used, one for each specification. For openapi specification handling, ```openapi``` object of ```ApiMetamodel2Openapi``` class is constructed and for swagger specification, ```swagg``` object of ```ApiMetamodel2Swagger``` class is created. To get into details of swagger 2.0 processing refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/api_endpoint/swagger2) and for opeanapi refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/api_endpoint/oas3)

### Part : 5.2
In this part, ```convert_path_list_to_path_map()``` takes in the ```path_list[]``` generated from above sections and converts it into a ```path_dict{}``` dictionary. The structure of the ```path_dict{}``` is {path: {method: pathObject}}. This method helps to combine the paths based on the methods present in them because same path can have multiple methods, e.g. /vCenter/VM can have get, patch, put etc.

### Part : 5.3
```cleanup()``` refines the ```path_list[]``` and ```type_dict{}```. In ```path_list[]``` it deletes the attributes **path** and **method** from the path object. For ```type_dict{}```, if required attribute is present inside properties of the type object, it is removed. The ```process_output()``` is used to serialize the data and create the swagger and openapi object out of it to be written into json files. ```api_swagg_fpp``` object is created for ```ApiSwaggerPathProcessing``` class and ```api_openapi_fpp``` for ```ApiOpenapiPathProcessing``` class to call ```process_output()``` specific to each specification.  For swagger serialization steps of /api endpoint refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/api_endpoint/swagger2) and for openapi refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/api_endpoint/oas3)