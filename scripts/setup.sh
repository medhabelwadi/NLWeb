#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_DIR=$SCRIPT_DIR/../

# includes
source "$SCRIPT_DIR/lib/shell_logger.sh"
source "$SCRIPT_DIR/lib/az.sh"
source "$SCRIPT_DIR/lib/state.sh"

declare random_prefix
declare resource_group_name
declare open_ai_resource_name
declare open_ai_resource_sku="s0"
declare openai_model_sku_capacity="1"
declare openai_model_sku_name="GlobalStandard"
declare subscription_id #will be set in az cli setup utility functions below
declare tenant_id #will be set in az cli setup utility functions below
declare location="eastus2"
declare rg_location="eastus"
declare DEBUG=false

function show_header(){
    local message="---- NLWeb Setup ---- "
    echo -e "${BOLD}${WHITE}${message}${NC}"
}

function main(){
    show_header
    configure_globals
    configure_env_file

    # check az cli
    check_az_cli_installed
    check_az_cli_logged_in
    set_subscription_id
    set_tenant_id

    # Create Resource Group
    _debug "> Creating resource group: $resource_group_name in location: $rg_location"
    az group create --name "$resource_group_name" --location "$rg_location"

    # Create an Azure OpenAI resource
    _debug "> Creating Azure OpenAPI resource: $open_ai_resource_name location: $location subscription: $subscription_id"
    az cognitiveservices account create \
    --name $open_ai_resource_name \
    --custom-domain $open_ai_resource_name \
    --resource-group $resource_group_name \
    --location $location \
    --kind OpenAI \
    --sku $open_ai_resource_sku \
    --subscription $subscription_id

    # get the endpoint url
    _debug "> Fetching OpenAI resource endpoint"
    open_ai_endpoint=$(az cognitiveservices account show --name $open_ai_resource_name --resource-group $resource_group_name | jq -r .properties.endpoint)
    _info "> Endpoint: $open_ai_endpoint"

    # get the primary api key
    _debug "> Fetching OpenAI resource primary key"
    open_ai_primary_key=$(az cognitiveservices account keys list --name $open_ai_resource_name  --resource-group $resource_group_name | jq -r .key1)
    _info_mask "> Primary key:" "$open_ai_primary_key"

    # add values to env file
    populate_env_file

    # deploy model gpt-4.1
    model="gpt-4.1"
    model_version="2025-04-14"
     _debug "> Deploying model: $model version: $model_version"
    az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $model \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "$openai_model_sku_capacity" \
    --sku-name "$openai_model_sku_name"
    _info "> Model deployed: $model"

    # deploy model gpt-4.1-turbo
    # deploy model gpt-4.1-mini
    model="gpt-4.1-mini"
    model_version="2025-04-14"
    _debug "> Deploying model: $model version: $model_version"
    az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $model \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "$openai_model_sku_capacity" \
    --sku-name "$openai_model_sku_name"
    _info "> Model deployed: $model"

    # deploy model text-embedding-3-small
    model="text-embedding-3-small"
    model_version="1"
     _debug "> Deploying model: $model version: $model_version"
    az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $model \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "$openai_model_sku_capacity" \
    --sku-name "$openai_model_sku_name"
    _info "> Model deployed: $model"

    export FOUNDRY_URL="https://ai.azure.com/resource/deployments?wsid=/subscriptions/$subscription_id/resourceGroups/$resource_group_name/providers/Microsoft.CognitiveServices/accounts/$open_ai_resource_name&tid=$tenant_id"
    save_deployment_state

    _success "Azure OpenAI resource and Models deployed!"
    _success "$FOUNDRY_URL"
}

# utilitites
function configure_globals(){
    # Check if ./.deployment exists and try to load random_prefix from it
    if [ -f ./.deployment ]; then
        existing_prefix=$(grep "^prefix=" ./.deployment | cut -d= -f2 | tr -d '[:space:]')
        if [ -n "$existing_prefix" ]; then
            random_prefix=$existing_prefix
            _info "Using existing prefix: $random_prefix"
        fi
    fi

    # Only generate a new prefix if one wasn't found
    if [ -z "$random_prefix" ]; then
        random_prefix=$(head /dev/urandom | tr -dc a-z0-9 | head -c 6)
        _info "prefix= $random_prefix" >> ./.deployment
        _info "Generated new prefix: $random_prefix"
    else
        # Ensure the file is up to date
        grep -q "^prefix=" ./.deployment || echo "prefix= $random_prefix" >> ./.deployment
    fi

    resource_group_name="nlweb-rg-$random_prefix"
    open_ai_resource_name="nlweb-oai-$random_prefix"
}

function populate_env_file(){
    # fetch Azure search secrets from Key Vault
    fetch_secret_from_keyvault "$SEARCH_ENDPOINT_SECRET_NAME" "SEARCH_ENDPOINT"
    fetch_secret_from_keyvault "$SEARCH_API_KEY_SECRET_NAME" "SEARCH_API_KEY"

    # replace placeholders from env template file
    sed -i "s|^AZURE_OPENAI_API_KEY=\"TODO\"|AZURE_OPENAI_API_KEY=\"$open_ai_primary_key\"|" ../code/.env 
    sed -i "s|^AZURE_OPENAI_ENDPOINT=\"https://TODO.openai.azure.com/\"|AZURE_OPENAI_ENDPOINT=\"$open_ai_endpoint\"|" ../code/.env
    sed -i "s|^AZURE_VECTOR_SEARCH_API_KEY=\"TODO\"|AZURE_VECTOR_SEARCH_API_KEY=\"$SEARCH_API_KEY\"|" ../code/.env 
    sed -i "s|^AZURE_VECTOR_SEARCH_ENDPOINT=\"https://TODO.search.windows.net\"|AZURE_VECTOR_SEARCH_ENDPOINT=\"$SEARCH_ENDPOINT\"|" ../code/.env
}


function configure_env_file(){
    cp "../code/.env.template" "../code/.env"

    local env_file="../code/.env"
    
    if [ ! -f "$env_file" ]; then
        echo -e "${RED}Environment file not found: $env_file${NC}"
        return 1
    else 
        echo "found env file!"
    fi
    
    # Read Key Vault settings
    azure_keyvault_name=$(grep "^AZURE_KEYVAULT_NAME=" "$env_file" | cut -d '"' -f 2 | tr -d '[:space:]')
    azure_keyvault_resource_group=$(grep "^AZURE_KEYVAULT_RESOURCE_GROUP=" "$env_file" | cut -d '"' -f 2)
    search_endpoint_secret_name=$(grep "^SEARCH_ENDPOINT_SECRET_NAME=" "$env_file" | cut -d '"' -f 2)
    search_api_key_secret_name=$(grep "^SEARCH_API_KEY_SECRET_NAME=" "$env_file" | cut -d '"' -f 2)

    # Check if any of the required Azure KeyVault variables are set to "TODO"
    local error_found=false
    local error_message="${RED}Error: The following required variables still have placeholder values:${NC}\n"
    
    if [ "$azure_keyvault_name" = "TODO" ]; then
        error_message+="  - ${YELLOW}AZURE_KEYVAULT_NAME${NC}\n"
        error_found=true
    fi
    
    if [ "$azure_keyvault_resource_group" = "TODO" ]; then
        error_message+="  - ${YELLOW}AZURE_KEYVAULT_RESOURCE_GROUP${NC}\n"
        error_found=true
    fi
    
    if [ "$search_endpoint_secret_name" = "TODO" ]; then
        error_message+="  - ${YELLOW}SEARCH_ENDPOINT_SECRET_NAME${NC}\n"
        error_found=true
    fi
    
    if [ "$search_api_key_secret_name" = "TODO" ]; then
        error_message+="  - ${YELLOW}SEARCH_API_KEY_SECRET_NAME${NC}\n"
        error_found=true
    fi

    if [ "$error_found" = true ]; then
        _error "$error_message"
        _error "Please update the file ${CYAN}../code/.env.template${NC} ${RED}file with the missing settings.\nNote: You only need to include values for the #Key Vault Settings# block, the rest will be populated by this setup script."
        exit 1
    fi

    # Debug output if needed
    if [ "$DEBUG" = true ]; then
        _debug "Key Vault Name: $azure_keyvault_name"
        _debug "Key Vault Resource Group: $azure_keyvault_resource_group"
        _debug "Search Endpoint Secret Name: $search_endpoint_secret_name"
        _debug "Search API Key Secret Name: $search_api_key_secret_name"
        
        # Mask sensitive information
        _info_mask "Azure Vector Search API Key:" "$azure_vector_search_api_key"
        _info_mask "Azure OpenAI API Key:" "$azure_openai_api_key"
    fi
    
    # Export variables to make them available to the rest of the script
    export AZURE_KEYVAULT_NAME="$azure_keyvault_name"
    export AZURE_KEYVAULT_RESOURCE_GROUP="$azure_keyvault_resource_group"
    export SEARCH_ENDPOINT_SECRET_NAME="$search_endpoint_secret_name"
    export SEARCH_API_KEY_SECRET_NAME="$search_api_key_secret_name"
    
 

    return 0
}


# parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug|-d)
            DEBUG=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# invoke main last to ensure all functions and variables are defined
main
