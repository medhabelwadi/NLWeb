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

function provision_oai(){
    
    configure_env_file
    
    # check az cli
    check_az_cli_installed
    check_az_cli_logged_in
    set_subscription_id
    set_tenant_id

    echo "----" > log.txt

    # Create Resource Group
    _debug "Creating resource group: $resource_group_name in location: $rg_location"
    output=$(az group create --name "$resource_group_name" --location "$rg_location")

    echo "Creating resource group: $resource_group_name in location: $rg_location" >> log.txt
    echo "$output" >> log.txt

    # Create an Azure OpenAI resource
    _debug "Creating Azure OpenAPI resource: $open_ai_resource_name location: $location subscription: $subscription_id"
    output=$(az cognitiveservices account create \
    --name $open_ai_resource_name \
    --custom-domain $open_ai_resource_name \
    --resource-group $resource_group_name \
    --location $location \
    --kind OpenAI \
    --sku $open_ai_resource_sku \
    --subscription $subscription_id)
    echo "Creating Azure OpenAPI resource: $open_ai_resource_name location: $location subscription: $subscription_id" >> log.txt
    echo "$output" >> log.txt

    # get the endpoint url
    _debug "Fetching OpenAI resource endpoint"
    open_ai_endpoint=$(az cognitiveservices account show --name $open_ai_resource_name --resource-group $resource_group_name | jq -r .properties.endpoint)
    _info "Endpoint: $open_ai_endpoint"

    # get the primary api key
    _debug "Fetching OpenAI resource primary key"
    open_ai_primary_key=$(az cognitiveservices account keys list --name $open_ai_resource_name  --resource-group $resource_group_name | jq -r .key1)
    _info_mask "Primary key:" "$open_ai_primary_key"

    # add values to env file
    populate_env_file

    # deploy model gpt-4.1
    model="gpt-4.1"
    model_version="2025-04-14"
    _debug "Deploying model: $model version: $model_version"
    output=$(az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $model \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "$openai_model_sku_capacity" \
    --sku-name "$openai_model_sku_name")
    echo "Deploying model: $model version: $model_version" >> log.txt
    echo "$output" >> log.txt
    _info "Model deployed: $model"

    # deploy model gpt-4.1-turbo
    # deploy model gpt-4.1-mini
    model="gpt-4.1-mini"
    model_version="2025-04-14"
    _debug "Deploying model: $model version: $model_version"
    output=$(az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $model \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "$openai_model_sku_capacity" \
    --sku-name "$openai_model_sku_name")
    echo "Deploying model: $model version: $model_version" >> log.txt
    echo "$output" >> log.txt
    _info "Model deployed: $model"

    # deploy model text-embedding-3-small
    model="text-embedding-3-small"
    model_version="1"
     _debug "Deploying model: $model version: $model_version"
    output=$(az cognitiveservices account deployment create \
    --name $open_ai_resource_name  \
    --resource-group  $resource_group_name \
    --deployment-name $model \
    --model-name $model \
    --model-version "$model_version"  \
    --model-format OpenAI \
    --sku-capacity "$openai_model_sku_capacity" \
    --sku-name "$openai_model_sku_name")
    echo "Deploying model: $model version: $model_version" >> log.txt
    echo "$output" >> log.txt
    _info "Model deployed: $model"

    export FOUNDRY_URL="https://ai.azure.com/resource/deployments?wsid=/subscriptions/$subscription_id/resourceGroups/$resource_group_name/providers/Microsoft.CognitiveServices/accounts/$open_ai_resource_name&tid=$tenant_id"
    save_deployment_state

    _success "Azure OpenAI resource and Models deployed!"
    _success "Foundry URL: $FOUNDRY_URL"
    _info "Deployment log file: ${REPO_DIR}log.txt"
}

# utilitites
function configure_globals(){
    # Check if ./.deployment exists and try to load random_prefix from it
    if [ -f ./.deployment ]; then
        existing_prefix=$(grep "^prefix=" ./.deployment | cut -d= -f2 | tr -d '[:space:]')
        if [ -n "$existing_prefix" ]; then
            random_prefix=$existing_prefix
            _debug "Using existing prefix: $random_prefix"
        fi
    fi

    # Only generate a new prefix if one wasn't found
    if [ -z "$random_prefix" ]; then
        random_prefix=$(head /dev/urandom | tr -dc a-z0-9 | head -c 6)
        echo "prefix= $random_prefix" >> ./.deployment
        _debug "Generated new prefix: $random_prefix"
    else
        # Ensure the file is up to date
        grep -q "^prefix=" ./.deployment || echo "prefix= $random_prefix" >> ./.deployment
    fi

    resource_group_name="nlweb-rg-$random_prefix"
    open_ai_resource_name="nlweb-oai-$random_prefix"
}

function populate_env_file(){
    # replace placeholders from env template file
    sed -i "s|^AZURE_OPENAI_API_KEY=\"<TODO>\"|AZURE_OPENAI_API_KEY=\"$open_ai_primary_key\"|" ${REPO_DIR}code/.env 
    sed -i "s|^AZURE_OPENAI_ENDPOINT=\"https://TODO.openai.azure.com/\"|AZURE_OPENAI_ENDPOINT=\"$open_ai_endpoint\"|" ${REPO_DIR}code/.env 
    sed -i "s|^AZURE_VECTOR_SEARCH_API_KEY_1=\"<TODO>\"|AZURE_VECTOR_SEARCH_API_KEY_1=\"$AZURE_VECTOR_SEARCH_API_KEY\"|" ${REPO_DIR}code/.env 
    sed -i "s|^AZURE_VECTOR_SEARCH_ENDPOINT_1=\"https://TODO.search.windows.net\"|AZURE_VECTOR_SEARCH_ENDPOINT_1=\"$AZURE_VECTOR_SEARCH_ENDPOINT\"|" ${REPO_DIR}code/.env 
}


function configure_env_file(){
    cp "${REPO_DIR}code/.env.template" "${REPO_DIR}code/.env"

    local env_file="${REPO_DIR}code/.env"
    
    if [ ! -f "$env_file" ]; then
        _error "Environment file not found: $env_file"
        return 1
    fi
    
    # Check if any of the required Azure Search are missing
    local error_found=false
    local error_message="${RED}Error: The following required environment variables do not have values:${NC}\n"
    
    if [ -z "$AZURE_VECTOR_SEARCH_API_KEY" ]; then
        error_message+="  - ${YELLOW}AZURE_VECTOR_SEARCH_API_KEY${NC}\n"
        error_found=true
    fi
    
    if [ -z "$AZURE_VECTOR_SEARCH_ENDPOINT" ]; then
        error_message+="  - ${YELLOW}AZURE_VECTOR_SEARCH_ENDPOINT${NC}\n"
        error_found=true
    fi


    if [ "$error_found" = true ]; then
        _error "$error_message"
        _error "Please configure the missing environment variables."
        exit 1
    fi

    # Debug output if needed
    if [ "$DEBUG" = true ]; then
        _debug "Azure Vector Search Endpoint: $AZURE_VECTOR_SEARCH_ENDPOINT"
        _debug_mask "Azure Vector Search API Key:" "$AZURE_VECTOR_SEARCH_API_KEY"
    fi
       
    return 0
}
