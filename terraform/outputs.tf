output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "openai_resource_name" {
  value = azurerm_cognitive_account.openai.name
}

output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "web_app_name" {
  value = azurerm_linux_web_app.main.name
}

output "web_app_url" {
  value = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "foundry_url" {
  value       = local.foundry_url
  description = "URL to access the Azure OpenAI Studio (Foundry)"
}

output "deployment_prefix" {
  value = local.random_prefix
}