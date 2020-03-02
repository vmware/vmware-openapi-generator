# vmware-open-api-generator

The documentation provides a guide to the working of VMWare Openapi Generator, the workflow execution and explanation of the work performed by each function. Prerequisites for understanding the documentation require being familiar with the structure of [swagger](https://swagger.io/docs/specification/2-0/what-is-swagger/) and [openapi](https://swagger.io/docs/specification/about/) specification files. 

The vmsgen.py is root of the program execution and it contains the main() function. The code is capable of generating openapi specification files from metamodel files by default. In order to generate the swagger 2.0 files, the -oas parameter has to be passed explicitly in the terminal. For better walk through of the code let's try to understand it in parts. 

Also familiarize yourself with the basic directory structure of the repository which goes as follows:
```
vmsgen.py
lib
    /api_endpoint
            /oas3
            /swagger2
    /rest_endpoint
            /oas3
            /swagger2
```
**For generating openapi specification files run:**
```
python3 vmsgen.py -k -vc <vcip> -c -o output 
```
**For generating swagger 2.0 specification files run:**
```
python3 vmsgen.py -k -vc <vcip> -c -o output -oas 2
```

## Part : 1
Refer the [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib) file of the lib folder to understand as to what this part of the code is doing.
``` python
def main():
    # Get user input.
    metadata_api_url, rest_navigation_url, output_dir, verify, enable_filtering, GENERATE_METAMODEL, SPECIFICATION, GENERATE_UNIQUE_OP_IDS = ec.get_input_params()
    # Maps enumeration id to enumeration info
    enumeration_dict = {}
    # Maps structure_id to structure_info
    structure_dict = {}
    # Maps service_id to service_info
    service_dict = {}
    # Maps service url to service id
    service_urls_map = {}
```
## Part : 2
The [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib) of the lib folder provides a detailed description of this section.
``` python
    start = timeit.default_timer()
    print('Trying to connect ' + metadata_api_url)
    session = requests.session()
    session.verify = False
    connector = get_requests_connector(session, url=metadata_api_url)
    if not enable_filtering:
        connector.set_application_context(ApplicationContext({SHOW_UNRELEASED_APIS: "True"}))
    print('Connected to ' + metadata_api_url)
    component_svc = ec.get_component_service(connector)
```
## Part : 3
The explanation of the below part can the found in this [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib) of the lib folder.
``` python
    dp.populate_dicts(component_svc, enumeration_dict, structure_dict, service_dict, service_urls_map, rest_navigation_url, GENERATE_METAMODEL)
    if enable_filtering:
        service_urls_map = dp.get_service_urls_from_rest_navigation(rest_navigation_url, verify)

    error_map = utils.build_error_map()

    package_dict_api, package_dict = dp.add_service_urls_using_metamodel(service_urls_map, service_dict, rest_navigation_url)
```
## Part : 4
You can find the description of the following part in this [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/rest_endpoint) under the lib/rest_endpoint section.
```python
    threads = []
    for package, service_urls in six.iteritems(package_dict):
        worker = threading.Thread(target=rest.process_service_urls, args=(
            package, service_urls, output_dir, structure_dict, enumeration_dict, service_dict, service_urls_map
            , error_map, rest_navigation_url, enable_filtering, SPECIFICATION, GENERATE_UNIQUE_OP_IDS))
        worker.daemon = True
        worker.start()
        threads.append(worker)
```
## Part : 5
Refer to [readme.md](https://github.com/Navneet-0101/vmware-openapi-generator/tree/master/lib/api_endpoint) under the lib/api_endpoint section for details.
```python
    for package, service_urls in six.iteritems(package_dict_api):
        worker = threading.Thread(target=api.process_service_urls, args=(
            package, service_urls, output_dir, structure_dict, enumeration_dict, service_dict, service_urls_map
            , error_map, rest_navigation_url, enable_filtering, SPECIFICATION, GENERATE_UNIQUE_OP_IDS))
        worker.daemon = True
        worker.start()
        threads.append(worker)
    for worker in threads:
        worker.join()
```
## Part : 6
As package_dict contains the packages of /rest endpoint and package_dict_api contains the packages of /api endpoint, these dictionaries are iterated individually to extract the package names stored in their respective keys which is appended to the api_files_list[]. The content of this list is written in the api.json file as a JSON object. After processing all the packages, the current system time is fetched in the stop variable, subtracted from the start time to get the time in which the swagger file has been generated.
```python
    api_files_list = []
    for name in list(package_dict.keys()):
        api_files_list.append("rest_"+name)

    for name in list(package_dict_api.keys()):
        api_files_list.append("api_"+name)

    api_files = { 'files': api_files_list }
    utils.write_json_data_to_file(output_dir + os.path.sep + 'api.json', api_files)
    stop = timeit.default_timer()
    print('Generated swagger files at ' + output_dir + ' for ' + metadata_api_url + ' in ' + str(
        stop - start) + ' seconds')
```
