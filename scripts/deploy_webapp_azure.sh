#!/usr/bin/env bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
REPO_DIR=$SCRIPT_DIR/../

# includes
source "$SCRIPT_DIR/lib/shell_logger.sh"
source "$SCRIPT_DIR/lib/az.sh"
source "$SCRIPT_DIR/lib/state.sh"

declare app_service_name

function main(){
    load_deployment_state
    load_env_file

    # configure web variables
    app_service_name="nlweb-appsvc-$random_prefix"
    web_app_name="nlweb-web-$random_prefix"
    resource_group_name="test_nlweb_hasho3_rg"
    acr_name="nlwebarc$random_prefix"
    
    # ensure resource group exsits this operation is idempotent
    az group create --name "$resource_group_name" --location "westus"
    az acr create --name "$acr_name" --resource-group "$resource_group_name"  --sku Standard
    # az acr login -n "$acr_name"

    # exit 0

    # deploy app service place
    az appservice plan create --name $app_service_name --resource-group $resource_group_name --sku P1v3 --is-linux

    # Create Web App with container configuration
    _info "Creating Web App: $web_app_name with container from ACR"
    az webapp create \
        --resource-group "$resource_group_name" \
        --plan "$app_service_name" \
        --name "$web_app_name" \
        --deployment-container-image-name "nlwebarceukxae.azurecr.io/nlweb:latest"
    
    # Assign system-assigned managed identity to web app
    _info "Assigning managed identity to Web App"
    az webapp identity assign --resource-group "$resource_group_name" --name "$web_app_name"
    
    # Get the principal ID of the web app's managed identity
    principal_id=$(az webapp identity show --resource-group "$resource_group_name" --name "$web_app_name" --query principalId --output tsv)
    
    # Grant the web app's managed identity access to the ACR
    _info "Granting ACR pull access to Web App"
    acr_id=$(az acr show --name "$acr_name" --resource-group "$resource_group_name" --query id --output tsv)
    az role assignment create --assignee "$principal_id" --scope "$acr_id" --role "AcrPull"
    
    # Configure continuous deployment from ACR
    _info "Configuring continuous deployment from ACR"
    az webapp config container set \
        --resource-group "$resource_group_name" \
        --name "$web_app_name" \
        --docker-registry-server-url "https://nlwebarceukxae.azurecr.io" \
        --docker-custom-image-name "nlwebarceukxae.azurecr.io/nlweb:latest" \
        --docker-registry-server-user "$(az acr credential show --name "$acr_name" --query username --output tsv)" \
        --docker-registry-server-password "$(az acr credential show --name "$acr_name" --query passwords[0].value --output tsv)"
    
    # # deploy web app
    # az webapp create --resource-group $resource_group_name --plan $app_service_name --name $web_app_name --runtime "PYTHON:3.13"

    # configure app settings
    az webapp config appsettings set --resource-group $resource_group_name --name $web_app_name --settings \
        AZURE_VECTOR_SEARCH_ENDPOINT="$AZURE_VECTOR_SEARCH_ENDPOINT" \
        AZURE_VECTOR_SEARCH_API_KEY="$AZURE_VECTOR_SEARCH_API_KEY" \
        AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
        AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
        WEBSITE_RUN_FROM_PACKAGE=1 \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true

    # az webapp config set --resource-group $resource_group_name --name $web_app_name --startup-file "startup.sh"

#     git archive --format zip --output ./app.zip main

#    # az webapp deployment source config-zip --resource-group $resource_group_name --name $web_app_name --src ./app.zip
#     az webapp deploy --src-path ./app.zip --type zip --name $web_app_name --resource-group $resource_group_name
}

# utility functions

function load_env_file(){
    local env_file="../code/.env"
    
    if [ ! -f "$env_file" ]; then
        _error "${RED}Environment file not found: $env_file${NC}"
        return 1
    fi
    
    # Read Key Vault settings
    vector_search_endpoint=$(grep "^AZURE_VECTOR_SEARCH_ENDPOINT=" "$env_file" | cut -d '"' -f 2 | tr -d '[:space:]')
    vector_search_api_key=$(grep "^AZURE_VECTOR_SEARCH_API_KEY=" "$env_file" | cut -d '"' -f 2)
    azure_openai_api_endpoint=$(grep "^AZURE_OPENAI_ENDPOINT=" "$env_file" | cut -d '"' -f 2)
    azure_openai_api_key=$(grep "^AZURE_OPENAI_API_KEY=" "$env_file" | cut -d '"' -f 2)

    
    # Export variables to make them available to the rest of the script
    export AZURE_VECTOR_SEARCH_ENDPOINT="$vector_search_endpoint"
    export AZURE_VECTOR_SEARCH_API_KEY="$vector_search_api_key"
    export AZURE_OPENAI_ENDPOINT="$azure_openai_api_endpoint"
    export AZURE_OPENAI_API_KEY="$azure_openai_api_key"
    
    return 0
}

# invoke main last to ensure all functions and variables are defined
main