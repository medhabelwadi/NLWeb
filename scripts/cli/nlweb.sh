#!/usr/bin/env bash

#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_DIR=$SCRIPT_DIR/../../

# includes
source "$SCRIPT_DIR/../lib/banner.sh"
source "$SCRIPT_DIR/../lib/shell_logger.sh"
source "$SCRIPT_DIR/../lib/az.sh"
source "$SCRIPT_DIR/../lib/state.sh"
source "$SCRIPT_DIR/../lib/aoai.sh"

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


function main(){
    show_banner
    configure_globals

    parse_args "$@"
    process_command
}

function usage(){
    echo "Usage: nlweb.sh [command] [options]"
    echo ""
}

function parse_args() {
  while (("$#")); do
    case "${1}" in
    setup)
        shift 1
        export command="setup"
        ;;
    check)
        shift 1
        export command="check"
        ;;    
    app)
        shift 1
        export command="app"
        ;;         
    view)
        shift 1
        export command="view"
        ;;
    cleanup)
        shift 1
        remove
        ;;
    -h | --help)
        shift 1
        export command="help"
        usage
        ;;
    -d | --debug)
        shift 1
        DEBUG=true
        shift 1
        ;;
    *) # preserve positional arguments
        PARAMS+="${1} "
        shift
        ;;
    esac
  done

  args=($PARAMS)
  if [[ -z "$command" ]]; then
    usage
  fi  
}

process_command() {
  case "$command" in
  setup)
    provision_oai
    ;;
  check)
    check
    ;;
  view)
    view
    ;;
  app)
    app
    ;;
  cleanup)
    remove
    ;;
  esac
}


function remove(){
    # check az cli
    check_az_cli_installed
    check_az_cli_logged_in
    
    load_deployment_state
    rm "${SCRIPT_DIR}/../.deployment"
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
        rm "$SCRIPT_DIR/../.deployment"
        echo -e "${GREEN}Resource deletion initiated. The process may take several minutes to complete.${NC}"
        echo -e "You can check the status in the Azure portal or by running:"
        echo -e "${CYAN}az group show --name \"$resource_group_name\"${NC}"
    else
        echo -e "\n${GREEN}Deletion cancelled. Your resources are safe.${NC}"
        exit 0
    fi
}

function view(){
    load_deployment_state
    _info "Azure AI Foundry: $FOUNDRY_URL"
}

function check(){
    pushd "$REPO_DIR/code" > /dev/null || exit 1
        python azure-connectivity.py 
    popd || exit 1
}

function app(){
    pushd "$REPO_DIR/code" > /dev/null || exit 1
        python app-file.py
    popd || exit 1
}

# invoke main last to ensure all functions and variables are defined
main "$@"

