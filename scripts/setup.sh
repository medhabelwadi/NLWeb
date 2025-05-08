#!/usr/bin/env bash

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

    # configure env file
    cp "../code/.env.template" "../code/.env"
    load_env_file
    fetch_secret_from_keyvault "$SEARCH_ENDPOINT_SECRET_NAME" "SEARCH_ENDPOINT"
    fetch_secret_from_keyvault "$SEARCH_API_KEY_SECRET_NAME" "SEARCH_API_KEY"

    sed -i "s|^AZURE_OPENAI_API_KEY=\"TODO\"|AZURE_OPENAI_API_KEY=\"$open_ai_primary_key\"|" ../code/.env 
    sed -i "s|^AZURE_OPENAI_ENDPOINT=\"https://TODO.openai.azure.com/\"|AZURE_OPENAI_ENDPOINT=\"$open_ai_endpoint\"|" ../code/.env
    sed -i "s|^AZURE_VECTOR_SEARCH_API_KEY=\"TODO\"|AZURE_VECTOR_SEARCH_API_KEY=\"$SEARCH_API_KEY\"|" ../code/.env 
    sed -i "s|^AZURE_VECTOR_SEARCH_ENDPOINT=\"https://TODO.search.windows.net\"|AZURE_VECTOR_SEARCH_ENDPOINT=\"$SEARCH_ENDPOINT\"|" ../code/.env

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

    save_deployment_state

    _info "https://ai.azure.com/resource/deployments?wsid=/subscriptions/$subscription_id/resourceGroups/$resource_group_name/providers/Microsoft.CognitiveServices/accounts/$open_ai_resource_name&tid=$tenant_id"
}

# utilitites
# color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
UNDERLINE='\033[4m'
NC='\033[0m' # No Color

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
function _debug(){
    local message="$1"
    
    if [ "$DEBUG" = true ]; then
        echo -e "${YELLOW}$message${NC}"
    fi
}
function _info_mask(){
    local label="$1"
    local message="$2"
    
    if [ "$DEBUG" = true ]; then
        message="$(echo "$message" | sed -E 's/^.*/****&/; s/^(.*)(.{4})$/****\2/')"
        _info "$label $message"
    fi
    
}

function _info(){
    local message="$1"
    
    if [ "$DEBUG" = true ]; then
        echo -e "${MAGENTA}$message\n${NC}"
    fi
}
function check_az_cli_logged_in(){
    if ! az account show &> /dev/null
    then
        echo -e "${RED}You are not logged in to Azure CLI. Please log in using 'az login'.${NC}"
        exit 1
    fi
}
function check_az_cli_installed(){
    if ! command -v az &> /dev/null
    then
        echo -e "${RED}Azure CLI is not installed and is a required dependency.\nhttps://learn.microsoft.com/cli/azure/install-azure-cli${NC}"
        exit 1
    fi
}

function set_subscription_id(){
    subscription_id=$(az account list --query "[?isDefault].id" -o tsv)
    if [ -z "$subscription_id" ]; then
        echo -e "${RED}No default subscription found. Please set a default subscription using 'az account set --subscription <subscription_name_or_id>'.${NC}"
        exit 1
    fi
}

function set_tenant_id(){
    tenant_id=$(az account list --query "[?isDefault].tenantId" -o tsv)
    if [ -z "$tenant_id" ]; then
        echo -e "${RED}No default tenant found. Please set a default tenant using 'az account set --subscription <subscription_name_or_id>'.${NC}"
        exit 1
    fi
}
function load_env_file(){
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
function save_deployment_state() {
    local deployment_file="./.deployment"
    
    # Create the file if it doesn't exist
    touch "$deployment_file"
    
    # Store variables in the file
    {
        echo "prefix=$random_prefix"
        echo "resource_group_name=$resource_group_name"
        echo "open_ai_resource_name=$open_ai_resource_name"
        echo "subscription_id=$subscription_id"
        echo "tenant_id=$tenant_id"
        echo "location=$location"
        echo "rg_location=$rg_location"
        echo "open_ai_resource_sku=$open_ai_resource_sku"
        echo "openai_model_sku_capacity=$openai_model_sku_capacity"
        echo "openai_model_sku_name=$openai_model_sku_name"
        echo "open_ai_endpoint=$open_ai_endpoint"
    } > "$deployment_file"
    
    _info "Deployment state saved to $deployment_file"
}

function fetch_secret_from_keyvault() {
    local secret_name="$1"
    local export_name="$2"
    local keyvault_name="${AZURE_KEYVAULT_NAME}"
    local resource_group="${AZURE_KEYVAULT_RESOURCE_GROUP}"
    
    if [ -z "$keyvault_name" ] || [ -z "$resource_group" ] || [ -z "$secret_name" ]; then
        echo -e "${RED}Error: Missing required variables for Key Vault access.${NC}"
        echo -e "${YELLOW}Required variables:${NC}"
        echo -e "  AZURE_KEYVAULT_NAME: ${keyvault_name:-Not set}"
        echo -e "  AZURE_KEYVAULT_RESOURCE_GROUP: ${resource_group:-Not set}"
        echo -e "  Secret Name: ${secret_name:-Not set}"
        return 1
    fi
    
    _debug "> Fetching secret '$secret_name' from Key Vault '$keyvault_name' in resource group '$resource_group'"
    
    # Ensure we're logged in and have access to the Key Vault
    if ! az keyvault show --name "$keyvault_name" --resource-group "$resource_group" > /dev/null 2>&1; then
        echo -e "${RED}Error: Could not access Key Vault. Please check your permissions and resource names.${NC}"
        return 1
    fi
    
    # Fetch the secret value
    local secret_value
    secret_value=$(az keyvault secret show --vault-name "$keyvault_name" --name "$secret_name" --query "value" -o tsv)
    _debug "> Secret value: $secret_value"
    if [ -z "$secret_value" ]; then
        echo -e "${RED}Error: Failed to retrieve secret or secret is empty.${NC}"
        return 1
    fi
    
    _debug "> Successfully retrieved secret '$secret_name'"
    echo "export $export_name=\"$secret_value\""
    eval "export $export_name=\"$secret_value\""
    return 0
}

function load_deployment_state() {
    local deployment_file="./.deployment"
    
    if [ ! -f "$deployment_file" ]; then
        echo -e "${RED}Error: Deployment file not found: $deployment_file${NC}"
        return 1
    fi
    
    _debug "> Loading deployment state from $deployment_file"
    
    # Load all variables directly by sourcing the file
    source "$deployment_file"
    
    # Explicitly set important variables to ensure they're properly loaded
    prefix=$(grep "^prefix=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    random_prefix="$prefix"
    resource_group_name=$(grep "^resource_group_name=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    open_ai_resource_name=$(grep "^open_ai_resource_name=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    subscription_id=$(grep "^subscription_id=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    tenant_id=$(grep "^tenant_id=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    location=$(grep "^location=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    rg_location=$(grep "^rg_location=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    open_ai_resource_sku=$(grep "^open_ai_resource_sku=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    openai_model_sku_capacity=$(grep "^openai_model_sku_capacity=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    openai_model_sku_name=$(grep "^openai_model_sku_name=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    open_ai_endpoint=$(grep "^open_ai_endpoint=" "$deployment_file" | cut -d= -f2 | tr -d '[:space:]')
    
    # Print loaded values if in debug mode
    if [ "$DEBUG" = true ]; then
        _debug "Loaded deployment variables:"
        _debug "  prefix/random_prefix: $random_prefix"
        _debug "  resource_group_name: $resource_group_name"
        _debug "  open_ai_resource_name: $open_ai_resource_name"
        _debug "  subscription_id: $subscription_id"
        _debug "  tenant_id: $tenant_id"
        _debug "  location: $location"
        _debug "  rg_location: $rg_location"
        _debug "  open_ai_endpoint: $open_ai_endpoint"
    fi
    
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
