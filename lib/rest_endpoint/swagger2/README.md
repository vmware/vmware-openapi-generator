# lib/rest_endpoint/swagger2/readme.md
This readme provides description of the files under swagger specification of the rest endpoint. On a brief note, ```rest_metamodel2swagger.py``` contains functions to handle request mapping paradigm of metamodel files. ```rest_swagger_parameter_handler.py``` contains functions which deal with path and query parameters for swagger 2.0 specification. ```rest_swagger_response_handler.py``` creates the response section for swagger files. And finally the ```rest_swagger_final_path_processing.py``` will create a path object with all the attributes such as operations, parameters, responses, schemas, consumes, produces etc.
# Part : 4.1.1
Continuing from section 4.1.1, here we look into the details of the ```get_path()```. This method takes in the operation info object as one of the parameters and extracts important information from it to build the swagger path specification such as documentation, parameters, errors, output and possible http method. ```find_consumes()``` determines the media type for input parameters in request body i.e. it returns the media type as **application/json** if http method is other than **get** and **delete**.

```python
def get_path(
        self,
        operation_info,
        http_method,
        url,
        service_name,
        type_dict,
        structure_dict,
        enum_dict,
        operation_id,
        error_map,
        enable_filtering):
    documentation = operation_info.documentation
    params = operation_info.params
    errors = operation_info.errors
    output = operation_info.output
    http_method = http_method.lower()
    consumes_json = self.find_consumes(http_method)
    produces = None
    par_array, url = self.handle_request_mapping(url, http_method, service_name,
                                                 operation_id, params, type_dict,
                                                 structure_dict, enum_dict, enable_filtering, rest_swagg_ph)
    response_map = rest_swagg_rh.populate_response_map(
        output,
        errors,
        error_map,
        type_dict,
        structure_dict,
        enum_dict,
        service_name,
        operation_id,
        enable_filtering)

    path_obj = utils.build_path(
        service_name,
        http_method,
        url,
        documentation,
        par_array,
        operation_id=operation_id,
        responses=response_map,
        consumes=consumes_json,
        produces=produces)
    self.post_process_path(path_obj)
    path = utils.add_basic_auth(path_obj)
    return path
```
From here onwards ```get_path()``` makes three important function calls to construct the swagger specification files.
# Function Call : 1 [handle_request_mapping()]
```handle_request_mapping()``` in ```RestMetamodel2Spec```parent class returns a list of parameter objects specific to http operations. It contains seperate methods to handle the parameters for http operations like put/post/patch, get and delete. Let's go through them one by one.
```python
def process_put_post_patch_request(
        url,
        service_name,
        operation_name,
        params,
        type_dict,
        structure_svc,
        enum_svc,
        enable_filtering,
        object):
    # Path
    path_param_list, other_param_list, new_url = utils.extract_path_parameters(
        params, url)
    par_array = []
    for field_info in path_param_list:
        parx = object.convert_field_info_to_swagger_parameter(
            'path', field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        par_array.append(parx)

    # Body
    body_param_list = other_param_list

    if body_param_list:
        parx = object.wrap_body_params(
            service_name,
            operation_name,
            body_param_list,
            type_dict,
            structure_svc,
            enum_svc,
            enable_filtering)
        if parx is not None:
            par_array.append(parx)

    return par_array, new_url
```
```process_put_post_patch_request()``` handles the path and body parameters inside the http operations of put, post and patch. It uses ```extract_path_parameters()``` to get a list of field info objects that are path variables and another list of field info objects which are not path variables and also handles the urls that changed due to mismatch of the parameter names.

The field info of path parameters is processed inside ```convert_field_info_to_swagger_parameters()``` which builds swagger parameter objects from metamodel field info objects. In order to achieve this it makes use of the RestTypeHandler class. This class determines the type of the field info object to be either **built-in**, **user-defined** or **generic** and caters to each of them under ```visit_builtin()```, ```visit_user_defined()``` and ```visit_generic()``` respectively.

```visit_builtin()```
1. Handles the native metamodel field info types such as date_time, secret, any_error, dymanic_structure, uri, binary, long, double and id.
2. Converts these API metamodel types to their equivalent swagger types inside ```metamodel_to_swagger_type_converter()```. A second value related to format information is also returned.
3. Constructs the swagger parameter object using the swagger type.

```visit_generic()```
1. Handles the generic metamodel field info types such as **optional**, **list**, **set**, **map** and recursively finds out the metamodel field types under each.
2. For field info type as map, it determines the types for map key and map values separately. The map key type is handled under generic or builtin types whereas map value type is once again recursively handled under builtin, generic or user-defined.
3. Constructs the swagger parameter object using the above types.

```visit_user_defined()```
1. Builds the parameter object using the resource id of user defined type.
2. Checks the user defined resource type to be structure or enumeration using ```check_type()```.

```check_type()```
1. Takes the resource type of user defined type, checks it to be mapping to either structure or enumeration type.
2. For each of these resource types, i.e structure or enumeration, fetches the structure or enumeration info from structure_dict{} and enum_dict{} respectively.
3. Deserializes the structure and enum info to construct a swagger parameter object.

The field info of body parameters is processed inside ```wrap_body_parameters()``` which creates a json wrapper around request body parameters. Parameter names are used as keys and parameter is itself used as the value. The function returns a parameter object with json wrapper around it.

```python
def process_get_request(
        url,
        params,
        type_dict,
        structure_svc,
        enum_svc,
        enable_filtering,
        object):
    param_array = []
    path_param_list, other_params_list, new_url = utils.extract_path_parameters(
        params, url)

    for field_info in path_param_list:
        parameter_obj = object.convert_field_info_to_swagger_parameter(
            'path', field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parameter_obj)

    # process query parameters
    for field_info in other_params_list:
        flattened_params = object.flatten_query_param_spec(
            field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        if flattened_params is not None:
            param_array = param_array + flattened_params
    return param_array, new_url
```
```process_get_request()``` also extracts the path and query parameters first. It deals with the field info of path parameters in the same manner as above but uses ```flatten_query_param_spec()``` to take care of the query parameters. The function creates a query parameter for every field info specification. If the field info is simple type i.e string or integer, then it is converted to swagger parameter. The query parameter type is an object but is converted to string as query parameter type object is not supported by swagger 2.0 specification.

```python
def process_delete_request(
        url,
        params,
        type_dict,
        structure_svc,
        enum_svc,
        enable_filtering,
        object):
    path_param_list, other_params, new_url = utils.extract_path_parameters(
        params, url)
    param_array = []
    for field_info in path_param_list:
        parx = object.convert_field_info_to_swagger_parameter(
            'path', field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parx)
    for field_info in other_params:
        parx = object.convert_field_info_to_swagger_parameter(
            'query', field_info, type_dict, structure_svc, enum_svc, enable_filtering)
        param_array.append(parx)
    return param_array, new_url
```
```process_delete_request()``` first extracts the path and non - path parameters list just like other http method processing functions have done. Creates parameter objects by using the field info of these lists and by processing the field info type. This method handles both the path and query parameters in a similar manner.

# Function Call : 2 [populate_response_map()]
```populate_response_map()``` uses the operation info's output object to extract the output object type. It takes care of two types of responses one which lead to a success and others which throw an error in order to populate the ```response_map{}```. It determines the schema of the success response by finding the output object's type using the TypeHandler class. If the schema is not void, a value wrapper for /rest endpoint response is created around the schema along with storing this response wrapper in ```type_dict{}```. For all the request codes that result in an 'ok' message, the success response is added as their value in the ```response_map{}```.

A failed response will be generated if there occurs an error in the execution of an operation. All the errors that can arise while executing an operation are listed in errors object of operation info. We iterate over these errors and get their corresponding response ```status_codes``` from ```error_map{}```. The type of the error is determined using TypeHandler class along with creating a schema object for that error. The ```response_map{}``` for these errors contains its key as the ```status_code``` of the error and value as a ```response_object``` having the documentation and schema for the error.

# Function Call : 3 [build_path()]
```build_path()``` function inside ```lib/utils.py``` serializes all the data extracted till now from metamodel files to build the path objects for the swagger specification. It takes in the service_name in order to generate tags based on the service names. Tags make it easy to refer to the operations of a resource inside a path. Other input parameters to this function include method type of the path, relative path to an individual endpoint, api documentation, input parameters for the api, api resonse and media types. All this information is wrapped in a path object and returned.

After creating the path object for swagger, ```post_process_path()``` performs some additions and subtractions in the path object. If the path object contains path attribute as ```/com/vmware/cis/session``` and http method as ```post```, a header parameter is added around the parameters attribute of the path object. If the operation id of the path object terminates with **$task**, ```add_query_parameters()``` is executed to add rudimentary support of adding query parameters to the path url. The query parameter ```vm-task=true``` is added as a query parameter at the end of the path url.

As a final step of processing the generated path object, security attribute in the form of Basic Authentication is added to the paths which require it using ```add_basic_auth()``` method. Finally the ```get_path()``` returns a processed path object.

## Part : 4.3
This section is in continuation from section 4.3 of ```lib/rest_endpoint.py/readme.md```. Here the working of ```process_output()``` is explained after ```path_dict{}``` has been created from path list. This method first performs some preprocessing steps on the path_dict{} and type_dict{} before initializing the final json object for swagger file.

The preprocessing steps are:
1. ```load_description()```: Load the description of swagger file into a dictionary to be added in swagger object.
2. ```remove_com_vmware_from_dict()```: As the name suggests, this method removes the 'com.vmware' from the definition(```type_dict{}```) and paths(```path_dict{}```) and also replaces the '$' with '_' from their keys.
3. ```create_unique_op_ids()```: Takes in ```path_dict{}``` as the input parameter and iterates through all the http operation array. For every operation, it gets the current operation id and calls the ```creates_camelized_op_id()```. It updates the path dictionary with the unique operation id after checking for uniqueness.
4. ```creates_camelized_operation_id()```: Takes the path, http_method and operation dictionary as input parameter. It then iterates through all the operation array to return the current operation id. Appends path to the existing operation id and replaces '/' and '-' with an underscore and removes 'com_vmware_' and splits the remaining string over '_' . Converts the first letter of all the words except the first one from lower to upper. Joins all the words together to returns the new camelcase string.
5. ```remove_query_parameters()```: Swagger specification does not allow to append query parameters to request mapping paths. Hence, this method will move the query parameters from request mapping to parameter section.

A swagger template containing attributes such as swagger specification info, host, security, rest navigation url, path object list(from ```path_dict{}```) and definition(from ```type_dict{}```) is created and written in the output directory in a json format by annotating the file name(package name) with 'rest'.
