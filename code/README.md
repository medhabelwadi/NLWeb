# NLWeb Azure Web App Deployment

This project has been adapted to run on Azure Web App. This README provides guidance on how to deploy and manage the application in Azure.

## Project Structure

```
project/
├── app.py                  # Entry point for Azure Web App
├── WebServer.py            # Modified WebServer for Azure
├── baseHandler.py          # Request handler
├── state.py                # State management
├── mllm.py                 # ML/LLM integration (modified for Azure)
├── retriever.py            # Data retrieval
├── azure_retrieve.py       # Azure AI Search integration
├── analyze_query.py        # Query analysis
├── decontextualize.py      # Query decontextualization
├── fastTrack.py            # Fast tracking
├── memory.py               # Memory management
├── post_prepare.py         # Post preparation
├── ranking.py              # Result ranking
├── relevance_detection.py  # Relevance detection
├── StreamingWrapper.py     # Streaming support
├── requirements.txt        # Python dependencies
├── env_loader.py           # Environment variable loader
├── gunicorn.conf.py        # Gunicorn configuration
├── web.config              # Azure Web App configuration
├── startup.sh              # Startup script
├── .env.template           # Template for environment variables
├── .deployment             # Azure deployment configuration
├── check_azure_connectivity.py # Connectivity checker
├── site_type.xml           # Site type definitions
└── static/                 # Static files directory
    └── html/               # HTML, CSS, JS files
```

## Prerequisites

1. Azure subscription
2. Azure CLI installed locally
3. Python 3.9+ installed locally (for testing)

## Local Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.template` and add your API keys

5. Run connectivity check:
   ```bash
   python check_azure_connectivity.py
   ```

6. Run the application locally:
   ```bash
   python app.py
   ```

## Deploying to Azure

### Option 1: Azure Portal Deployment

1. Create a Web App in Azure Portal:
   - Choose Python 3.9 as the runtime stack
   - Select Linux as the operating system

2. Set up deployment source:
   - Choose GitHub or Azure DevOps
   - Connect to your repository
   - Set up continuous deployment

3. Configure application settings:
   - Add all the environment variables from `.env.template`
   - Set `WEBSITE_RUN_FROM_PACKAGE=1`
   - Set `SCM_DO_BUILD_DURING_DEPLOYMENT=true`

4. Configure startup command:
   ```
   startup.sh
   ```

### Option 2: Azure CLI Deployment

1. Log in to Azure:
   ```bash
   az login
   ```

2. Create a resource group (if needed):
   ```bash
   az group create --name yourResourceGroup --location eastus
   ```

3. Create an App Service Plan:
   ```bash
   az appservice plan create --name yourAppServicePlan --resource-group yourResourceGroup --sku B1 --is-linux
   ```

4. Create a Web App:
   ```bash
   az webapp create --resource-group yourResourceGroup --plan yourAppServicePlan --name yourWebAppName --runtime "PYTHON|3.9"
   ```

5. Configure environment variables:
   ```bash
   az webapp config appsettings set --resource-group yourResourceGroup --name yourWebAppName --settings \
     AZURE_SEARCH_API_KEY="your_key_here" \
     AZURE_EMBEDDING_API_KEY="your_key_here" \
     AZURE_OPENAI_API_KEY="your_key_here" \
     AZURE_DEEPSEEK_KEY="your_key_here" \
     OPENAI_API_KEY="your_key_here" \
     ANTHROPIC_API_KEY="your_key_here" \
     WEBSITE_RUN_FROM_PACKAGE=1
   ```

6. Set startup command:
   ```bash
   az webapp config set --resource-group yourResourceGroup --name yourWebAppName --startup-file "startup.sh"
   ```

7. Deploy code using ZIP deployment:
   ```bash
   # Create a ZIP file of your project
   git archive --format zip --output ./app.zip main
   
   # Deploy the ZIP file
   az webapp deployment source config-zip --resource-group yourResourceGroup --name yourWebAppName --src ./app.zip
   ```

## Monitoring and Troubleshooting

### Logs
View logs in Azure Portal or using Azure CLI:
```bash
az webapp log tail --name yourWebAppName --resource-group yourResourceGroup
```

### Diagnostic Tools
Azure App Service provides diagnostic tools in the Azure Portal:
1. Go to your Web App
2. Navigate to "Diagnose and solve problems"
3. Choose from available diagnostics tools

### Health Check
The application includes a health endpoint at `/health` that returns a JSON response indicating service health.

## More Information

For more detailed information, see:
- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)
- [Python on App Service](https://docs.microsoft.com/en-us/azure/app-service/configure-language-python)
- Check the [Azure Web App Deployment Guide](./Azure_Web_App_Deployment_Guide.md) for detailed deployment instructions.
