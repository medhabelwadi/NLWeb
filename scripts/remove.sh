#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_DIR=$SCRIPT_DIR/../

# includes
source "$SCRIPT_DIR/lib/shell_logger.sh"
source "$SCRIPT_DIR/lib/az.sh"
source "$SCRIPT_DIR/lib/state.sh"


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
    echo -e "${RED}We found the following resources:${NC}"
    echo -e "${BOLD}Resource Group:${NC} ${RED}$resource_group_name${NC}"
    echo -e "${BOLD}Azure OpenAI Service:${NC} ${RED}$open_ai_resource_name${NC}"
    
    # Ask for confirmation
    echo -e "\n${RED}WARNING: This will permanently delete these resources and all their contents.${NC}"
    read -p "Are you sure you want to delete these resources? (yes/no): " confirm
    
    if [[ "$confirm" =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "\n${BOLD}Proceeding with deletion...${NC}"
        
        # Add resource deletion code here
        _debug "Deleting resource group: $resource_group_name"
        az group delete --name "$resource_group_name" --yes --no-wait
        rm ./.deployment
        echo -e "${GREEN}Resource deletion initiated. The process may take several minutes to complete.${NC}"
        echo -e "You can check the status in the Azure portal or by running:"
        echo -e "${CYAN}az group show --name \"$resource_group_name\"${NC}"
    else
        echo -e "\n${GREEN}Deletion cancelled. Your resources are safe.${NC}"
        exit 0
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
