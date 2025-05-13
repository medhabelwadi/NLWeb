#!/usr/bin/env bash

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
        echo "foundry_url=$FOUNDRY_URL"
    } > "$deployment_file"
    
    _info "Deployment state saved to $deployment_file"
}

function load_deployment_state() {
    local deployment_file="./.deployment"
    
    if [ ! -f "$deployment_file" ]; then
        echo -e "${RED}Error: Deployment file not found: $deployment_file${NC}"
        exit 1
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
    FOUNDRY_URL=$(grep "^foundry_url=" "$deployment_file" | sed 's/^foundry_url=//' | tr -d '[:space:]')
    
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
