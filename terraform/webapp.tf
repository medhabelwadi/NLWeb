# Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = local.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = var.web_app_location
  sku                 = var.acr_sku
  admin_enabled       = true
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = local.app_service_name
  resource_group_name = azurerm_resource_group.main.name
  location            = var.web_app_location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
}

# Web App
resource "azurerm_linux_web_app" "main" {
  name                = local.web_app_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_service_plan.main.location
  service_plan_id     = azurerm_service_plan.main.id

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    AZURE_VECTOR_SEARCH_ENDPOINT   = data.azurerm_key_vault_secret.search_endpoint.value
    AZURE_VECTOR_SEARCH_API_KEY    = data.azurerm_key_vault_secret.search_api_key.value
    AZURE_OPENAI_ENDPOINT          = azurerm_cognitive_account.openai.endpoint
    AZURE_OPENAI_API_KEY           = azurerm_cognitive_account.openai.primary_access_key
    WEBSITE_RUN_FROM_PACKAGE       = "1"
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
  }

  site_config {
    container_registry_use_managed_identity = true

    application_stack {
      docker_image_name   = "${var.container_image}:${var.container_tag}"
      docker_registry_url = "https://${azurerm_container_registry.acr.login_server}"
    }
  }
}

# Role assignment for ACR Pull
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.main.identity[0].principal_id
}