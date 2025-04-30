import utils
from xml.etree import ElementTree as ET
import json 
from azure_logger import log

BASE_NS = "http://nlweb.ai/base"

# This file deals with getting the right prompt for a given
# type, site and prompt-name. 
# Also deals with filling in the prompt.
# #Yet to do the subclass check.

prompt_roots = []
def init_prompts (files = ["html/site_type.xml"]):
    global prompt_roots
    for file in files:
        prompt_roots.append(ET.parse(file).getroot())


def super_class_of(child_class, parent_class):
    if parent_class == child_class:
        return True
    if parent_class == "{" + BASE_NS + "}Thing" :
        return True
    return False

prompt_var_cache = {}
def get_prompt_variables_from_prompt(prompt):
    if prompt in prompt_var_cache:
        return prompt_var_cache[prompt]
    variables = extract_variables_from_prompt(prompt)
    prompt_var_cache[prompt] = variables
    return variables

def extract_variables_from_prompt(prompt):
    # Find all strings between { and }
    variables = set()
    start = 0
    while True:
        # Find next opening brace
        start = prompt.find('{', start)
        if start == -1:
            break
            
        # Find matching closing brace
        end = prompt.find('}', start)
        if end == -1:
            break
            
        # Extract variable name and add to set
        var = prompt[start+1:end].strip()
        variables.add(var)
        
        # Move start position
        start = end + 1
        
    return variables

def get_prompt_variable_value(variable, handler):
    site = handler.site
    query = handler.query
    prev_queries = handler.prev_queries

    if variable == "request.site":
        return site
    elif variable == "site.itemType":
        item_type = handler.item_type
        return item_type.split("}")[1]
    elif variable == "request.query":
        if (handler.state.is_decontextualization_done()):
            return handler.decontextualized_query
        elif (len(prev_queries) > 0):
            return query + " previous queries: " + str(prev_queries)
        else:
            return query
    elif variable == "request.previousQueries":
        return str(prev_queries)
    elif variable == "request.contextUrl":
        return handler.context_url
    elif variable == "request.itemType":
        return handler.item_type
    elif variable == "request.contextDescription":
        return handler.context_description
    elif variable == "request.rawQuery":
        return query
    elif variable == "request.answers":
        return str(handler.final_ranked_answers)
    else:
        return ""

def fill_prompt(prompt_str, handler):
    variables = get_prompt_variables_from_prompt(prompt_str)
    for variable in variables:
        value = get_prompt_variable_value(variable, handler)        
        prompt_str = prompt_str.replace("{" + variable + "}", value)
    return prompt_str

def fill_ranking_prompt(prompt_str, handler, description):
    try:
        variables = get_prompt_variables_from_prompt(prompt_str)
        for variable in variables:
            try:
                if (variable == "item.description"):
                    value = json.dumps(description)
                else:
                    value = get_prompt_variable_value(variable, handler)
                prompt_str = prompt_str.replace("{" + variable + "}", value)
            except Exception as e:
                print(f"Error processing variable '{variable}': {str(e)}")
                # Use a placeholder to indicate error
                prompt_str = prompt_str.replace("{" + variable + "}", f"[ERROR: {str(e)}]")
        return prompt_str
    except Exception as e:
        print(f"Error in fill_ranking_prompt: {str(e)}")
        # Return original prompt string with error message
        return f"{prompt_str}\n[ERROR in fill_ranking_prompt: {str(e)}]"

cached_prompts = {}
def get_cached_values(site, item_type, prompt_name):
    cache_key = (site, item_type, prompt_name)
    if cache_key in cached_prompts:
        return cached_prompts[cache_key]
    return None

def find_prompt(site, item_type, prompt_name):  
    if (prompt_roots == []):
        init_prompts()
    cached_values = get_cached_values(site, item_type, prompt_name)
    if cached_values is not None:
        return cached_values

    BASE_NS = "http://nlweb.ai/base"
    SITE_TAG = "{" + BASE_NS + "}Site"
    PROMPT_TAG = "{" + BASE_NS + "}Prompt"
    PROMPT_STRING_TAG = "{" + BASE_NS + "}promptString"
    RETURN_STRUC_TAG = "{" + BASE_NS + "}returnStruc"
    # First, try to find a Site element matching the site parameter
    site_element = None
    prompt_element = None
    for root_element in prompt_roots:
        for site_element in root_element.findall(SITE_TAG):
            if site_element.get("ref") == site:
                break
    candidate_roots = []
    if site_element is not None:
        candidate_roots.append(site_element)
    else:
        candidate_roots = prompt_roots
    # If site element found, search for matching Type element within it
    for candidate_root in candidate_roots:
        for child in candidate_root:
            if (super_class_of(item_type, child.tag)):
                children = child.findall(PROMPT_TAG)
                for pe in children:
                    if pe.get("ref") == prompt_name:
                        prompt_element = pe
                        break
    if prompt_element is not None:
        prompt_text = prompt_element.find(PROMPT_STRING_TAG).text
        return_struc_text = prompt_element.find(RETURN_STRUC_TAG).text
        return_struc_text = return_struc_text.strip()
        if return_struc_text == "":
            return_struc = None
        else:
            return_struc = json.loads(return_struc_text)    
        cached_prompts[(site, item_type, prompt_name)] = (prompt_text, return_struc)
        return prompt_text, return_struc
    else:
        cached_prompts[(site, item_type, prompt_name)] = (None, None)
        return None, None


def get_prompt_variables_from_file(xml_file_path):
    """
    Parse XML file and extract variables from promptString elements.
    Returns a set of all variables found.
    """
    import xml.etree.ElementTree as ET
    
    try:
        # Parse XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Find all promptString elements recursively
        all_variables = set()
        
        def process_element(element):
            # Check if current element is a promptString
          #  print(element.tag)
            if element.tag == '{http://nlweb.ai/base}promptString':
                prompt_text = element.text
                if prompt_text:
                    variables = extract_variables_from_prompt(prompt_text)
                    all_variables.update(variables)
            
            # Recursively process all child elements
            for child in element:
                process_element(child)
                
        # Start recursive processing from root
        process_element(root)
        return all_variables
        
    except ET.ParseError as e:
        print(f"Error parsing XML file {xml_file_path}: {str(e)}")
        return set()
    except FileNotFoundError:
        print(f"XML file not found: {xml_file_path}")
        return set()
    except Exception as e:
        print(f"Error processing file {xml_file_path}: {str(e)}")
        return set()

#print(get_prompt_variables_from_file("html/site_type.xml"))