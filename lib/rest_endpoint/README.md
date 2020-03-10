# lib/rest_endpoint/readme.md
The rest_endpoint directory contains the ```rest_url_processing.py``` file which provides functionality to process the /rest endpoint specific urls and generate either openapi or swagger files depending upon the user requirement. The ```restUrlProcessing``` class encapuslates the functions specific to /rest endpoint processing and inherits the ```urlProcessing``` class defined inside the ```lib/url_processing.py``` which contains functionalities common to /api and /rest endpoints. ```rest_type_handler.py``` takes care of the structure and enumeration type processing for populating the ```type_dict{}``` of the ```process_service_urls()``` and inherits from ```lib/type_handler_common.py``` where type handling features common to /api and /rest have been taken care of. In ```rest_metamodel2spec.py```, functions to get the path and process its http operations for /rest endpoint api's are listed.

## Part : 4
This part makes use of multi-threading to process each **rest endpoint package** independently as a thread and then join these threads together. ```process_service_urls()``` is the entry point function for processing the service urls. It is called by creating an object of ```restUrlProcessing``` class. Since this function leads to a couple of other major function calls, let's try to get a hold of it in parts. It takes in service_urls of a package for each thread along with couple of other parameters which are processed one by one to deserialize the metadata they contain.
```python
def process_service_urls(self,package_name, service_urls, 
                        output_dir,structure_dict, enum_dict, service_dict, 
                        service_url_dict, error_map, rest_navigation_url, 
                        enable_filtering, spec, gen_unique_op_id):
        print('processing package ' + package_name + os.linesep)
        type_dict = {}
        path_list = []
        # PART : 4.1 
        for service_url in service_urls:
            service_name, service_end_point = service_url_dict.get(service_url, None)
            service_info = service_dict.get(service_name, None)
            if service_info is None:
                continue
            if utils.is_filtered(service_info.metadata, enable_filtering):
                continue
        # PART : 4.1.1        
            if self.contains_rm_annotation(service_info):
                for operation in service_info.operations.values():
                    url, method = self.find_url_method(operation)
                    operation_id = operation.name
                    op_metadata = service_info.operations[operation_id].metadata
                    if utils.is_filtered(op_metadata, enable_filtering):
                        continue
                    operation_info = service_info.operations.get(operation_id)

                    if spec == '2':
                        path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)
                    if spec == '3':
                        path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)

                    path_list.append(path)
                continue
        # PART : 4.1.2
            service_operations = utils.get_json(rest_navigation_url + service_url + '?~method=OPTIONS', False)
            if service_operations is None:
                continue

            for service_operation in service_operations:
                service_name = service_operation['service']
                service_info = service_dict.get(service_name, None)
                if service_info is None:
                    continue
                operation_id = service_operation['name']
                if operation_id not in service_info.operations:
                    continue
                op_metadata = service_info.operations[operation_id].metadata
                if utils.is_filtered(op_metadata, enable_filtering):
                    continue
                url, method = self.find_url(service_operation['links'])
                url = self.get_service_path_from_service_url(url, rest_navigation_url)
                operation_info = service_info.operations.get(operation_id)

                if spec == '2':
                    path = swagg.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)
                if spec == '3':
                    path = openapi.get_path(operation_info, method, url, service_name, type_dict, structure_dict, enum_dict,
                                    operation_id, error_map, enable_filtering)

                path_list.append(path)
        # PART : 4.2 
        path_dict = self.convert_path_list_to_path_map(path_list)
        # PART : 4.3 
        self.cleanup(path_dict=path_dict, type_dict=type_dict)
        if spec == '2':
            rest_swagg_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)    
        if spec== '3':
            rest_openapi_fpp.process_output(path_dict, type_dict, output_dir, package_name, gen_unique_op_id)     
```
### Part : 4.1
We start iterating through rest service urls corresponding to each package and get the service name from ```service_urls_map{}``` for each service url. Using the service name, the metamodel information for each service is extracted from ```service_dict{}``` and stored as a ```service_info``` object. A ```service_info``` object contains the following attributes:
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
    _rest_convertor_mode:

}
```
If service info object is none or its metadata contains keywords 'changing' or 'proposed', the service info is ignored for processing. 
#### Part : 4.1.1
In ```contains_rm_annotations()``` it is checked if the operation's metadata under a service contains request mapping or not i.e. contains details about the method type, the url to request and query paramteres of the operation. If request mapping exists, ```the find_url_method()``` is used to extract the url and methods of the service's operations using operation information parameter. ```get_path()``` is the most important function which takes in operation info and constructs swagger based path specifications. Since path specifications and handling of parameters, responses is a bit different for swagger 2.0 and openapi, two copies of the function are used, one for each specification. For openapi specification handling, ```openapi``` object of ```restMetamodel2Openapi``` class is constructed and for swagger specification, ```swagg``` object of ```restMetamodel2Swagger``` is created. To get into details of swagger 2.0 processing refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/rest_endpoint/swagger2) and for opeanapi refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/rest_endpoint/oas3)
#### Part : 4.1.2
The previous section dealt with processing of service_urls which come with request mapping whereas this section deals with taking care of the older versions of vModel2 files which were designed when /rest endpoints were not in picture. Therefore, a special request mapping is produced in their case by making a get request to service url coupled with rest navigation url and query parameter **METHOD** set to **OPTIONS**. This request if successful returns a list of service operation objects. We iterate through each of these to get the service name and service info. Just as in the above section, we found the url and method for each operation inside the service, here also we do the same but with the ```find_url()``` method. It takes in the list of urls inside a service operation and tries to pick the best url and its corresponding method. The logic for picking the best url is simple. If there is only one url, the job is done. If there are more than one urls then we pick the one that does not contain ~action but contains id:{}. ```get_service_path_from_service_url()``` strips the base url from service url and returns the remaining url. The ```get_path()``` function here remains the same as in 4.1.1 section.

### Part : 4.2
In this part, ```convert_path_list_to_path_map()``` takes in the ```path_list[]``` generated from above sections and converts it into a ```path_dict{}``` dictionary. The structure of the ```path_dict{}``` is { path : {method : pathObject }}. This method helps to combine the paths based on the methods present in them because same path can have multiple methods, e.g. /vCenter/VM can have get, patch, put etc. 

### Part : 4.3 
```cleanup()``` refines the ```path_list[]``` and ```type_dict{}```. In ```path_list[]``` it deletes the attributes **path** and **method** from the path object. For ```type_dict{}```, if required attribute is present inside properties of the type object, it is removed. The ```process_output()``` is used to serialize the data and create the swagger and openapi object out of it to be written into json files. ```rest_swagg_fpp``` object is created for ```restSwaggerPathProcessing``` class and ```rest_openapi_fpp``` for ```restOpenapiPathProcessing``` class to call ```process_output()``` specific to each specification. For swagger serialization steps refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/rest_endpoint/swagger2) and for openapi refer [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/rest_endpoint/oas3)

