#!/usr/bin/env bash

declare resource_group_name
declare DEBUG=false

function show_header(){
    local message="---- NLWeb Cleanup ---- "
    echo -e "${BOLD}${WHITE}${message}${NC}"
}

function main(){
    show_header

    # check az cli
    check_az_cli_installed
    check_az_cli_logged_in
    
    load_deployment_state

    # Display resource information
    echo -e "${GREEN}We found the following resources:${NC}"
    echo -e "${BOLD}Resource Group:${NC} ${CYAN}$resource_group_name${NC}"
    echo -e "${BOLD}Azure OpenAI Service:${NC} ${CYAN}$open_ai_resource_name${NC}"
    
    # Ask for confirmation
    echo -e "\n${YELLOW}WARNING: This will permanently delete these resources and all their contents.${NC}"
    read -p "Are you sure you want to delete these resources? (yes/no): " confirm
    
    if [[ "$confirm" =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "\n${BOLD}Proceeding with deletion...${NC}"
        
        # Add resource deletion code here
        _debug "Deleting resource group: $resource_group_name"
        # az group delete --name "$resource_group_name" --yes --no-wait
        
        echo -e "${GREEN}Resource deletion initiated. The process may take several minutes to complete.${NC}"
        echo -e "You can check the status in the Azure portal or by running:"
        echo -e "${CYAN}az group show --name \"$resource_group_name\"${NC}"
    else
        echo -e "\n${GREEN}Deletion cancelled. Your resources are safe.${NC}"
        exit 0
    fi
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
