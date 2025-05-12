# Azure OpenAI Cognitive Account
resource "azurerm_cognitive_account" "openai" {
  name                  = local.openai_resource_name
  location              = var.location
  resource_group_name   = azurerm_resource_group.main.name
  kind                  = "OpenAI"
  sku_name              = var.openai_sku
  custom_subdomain_name = local.openai_resource_name

  tags = {
    application = "nlweb"
  }
}

# Model deployments using for_each
resource "azurerm_cognitive_deployment" "models" {
  for_each = var.openai_models  # Changed from local.openai_models to var.openai_models

  name                 = each.value.name
  cognitive_account_id = azurerm_cognitive_account.openai.id

  model {
    format  = "OpenAI"
    name    = each.value.name
    version = each.value.version
  }

  sku {
    name     = var.openai_model_sku_name
    capacity = var.openai_model_sku_capacity
  }

  depends_on = [azurerm_cognitive_account.openai]
}

# Access Key Vault for Vector Search
data "azurerm_key_vault" "existing" {
  name                = var.keyvault_name
  resource_group_name = var.keyvault_resource_group
}

data "azurerm_key_vault_secret" "search_endpoint" {
  name         = var.search_endpoint_secret_name
  key_vault_id = data.azurerm_key_vault.existing.id
}

data "azurerm_key_vault_secret" "search_api_key" {
  name         = var.search_api_key_secret_name
  key_vault_id = data.azurerm_key_vault.existing.id
}

# Create OpenAI API Key secret for consistency
resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "openai-api-key-${local.random_prefix}"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = data.azurerm_key_vault.existing.id
}

# Generate .env file from template
resource "local_file" "env_file" {
  content = templatefile(local.env_template_path, {
    AZURE_KEYVAULT_NAME           = var.keyvault_name,
    AZURE_KEYVAULT_RESOURCE_GROUP = var.keyvault_resource_group,
    SEARCH_ENDPOINT_SECRET_NAME   = var.search_endpoint_secret_name,
    SEARCH_API_KEY_SECRET_NAME    = var.search_api_key_secret_name,
    AZURE_OPENAI_API_KEY          = azurerm_cognitive_account.openai.primary_access_key,
    AZURE_OPENAI_ENDPOINT         = azurerm_cognitive_account.openai.endpoint,
    AZURE_VECTOR_SEARCH_API_KEY   = data.azurerm_key_vault_secret.search_api_key.value,
    AZURE_VECTOR_SEARCH_ENDPOINT  = data.azurerm_key_vault_secret.search_endpoint.value
  })
  filename   = local.env_file_path
  depends_on = [azurerm_cognitive_account.openai]
}