#!/usr/bin/env bash

declare random_prefix
random_prefix="dev2" #$(head /dev/urandom | tr -dc a-z0-9 | head -c 6)

declare resource_group_name="nlweb-rg-$random_prefix"
declare open_ai_resource_name="nlweb-oai-$random_prefix"
declare open_ai_gpt41_model_name="nlweb-gpt41-$random_prefix"
declare open_ai_gpt41mini_model_name="nlweb-gpt41mini-$random_prefix"
declare open_ai_embeddingsmall_model_name="nlweb-embeddingsmall-$random_prefix"
declare subscription_id #will be set in az cli setup utility functions below
declare tenant_id #will be set in az cli setup utility functions below
declare location="eastus2"
declare DEBUG=false

function show_header(){
    local message="---- NLWeb Infrastructure Setup ---- "
    echo -e "${BOLD}${WHITE}${message}${NC}"
}

function main(){
    show_header

    # check az cli
    check_az_cli_installed
    check_az_cli_logged_in
    set_subscription_id
    set_tenant_id

    # Create Resource Group
    _debug "> Creating resource group: $resource_group_name in location: $location"
    az group create --name "$resource_group_name" --location "$location"

    # Create an Azure OpenAI resource
    _debug "> Creating Azure OpenAPI resource: $open_ai_resource_name location: $location subscription: $subscription_id"
    az cognitiveservices account create \
    --name $open_ai_resource_name \
    --resource-group $resource_group_name \
    --location $location \
    --kind OpenAI \
    --sku s0 \
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
    cp "./code/.env.template" "./code/.env"
    sed -i "s|^AZURE_OPENAI_API_KEY=\"TODO\"|AZURE_OPENAI_API_KEY=\"$open_ai_primary_key\"|" ./code/.env 
    sed -i "s|^AZURE_OPENAI_ENDPOINT=\"https://TODO.openai.azure.com/\"|AZURE_OPENAI_ENDPOINT=\"$open_ai_endpoint\"|" ./code/.env
    
    # deploy model gpt-4.1
    model="gpt-4.1"
    model_version="2025-04-14"
     _debug "> Deploying model: $model version: $model_version"
    az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $open_ai_gpt41_model_name \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "GlobalStandard"
    _info "> Model deployed: $open_ai_gpt41_model_name"

    # deploy model gpt-4.1-mini
    model="gpt-4.1-mini"
    model_version="2025-04-14"
    _debug "> Deploying model: $model version: $model_version"
    az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $open_ai_gpt41mini_model_name \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "GlobalStandard"
    _info "> Model deployed: $open_ai_gpt41mini_model_name"

    # deploy model text-embedding-3-small
    model="text-embedding-3-small"
    model_version="1"
     _debug "> Deploying model: $model version: $model_version"
    az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $open_ai_embeddingsmall_model_name \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "1" \
    --sku-name "Standard"
    _info "> Model deployed: $open_ai_embeddingsmall_model_name"

    _info "https://ai.azure.com/resource/playground?wsid=/subscriptions/$subscription_id/resourceGroups/$resource_group_name/providers/Microsoft.CognitiveServices/accounts/$open_ai_resource_name&tid=$tenant_id"
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

function _debug(){
    local message="$1"
    
    if [ "$DEBUG" = true ]; then
        echo -e "${YELLOW}$message${NC}"
    fi
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
