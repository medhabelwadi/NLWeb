# NLWeb

Add LLM chat functionality to your existing web pages by leveraging your site schema

-----------------------------------------------------------------

## Getting Started

Use these instructions to run an NLWeb server - below we have instructions for:
- [Running an NLWeb service locally](#local-app-setup)
- [Deploying a Local Database](#deploying-a-local-database)
- [Loading Data into your Local Database](#loading-data-into-your-local-database)


## Prerequisites

These instructions assume that you have Python 3.10+ installed locally.


## Local App Setup

1. Clone or download this repository.
```
git clone https://github.com/microsoft/NLWeb
cd NLWeb
```

2. Create a virtual environment. 
```
python -m venv myenv
```

3. Activate the virtual environment.   
```
source myenv/bin/activate    # Or on Windows: myenv\Scripts\activate
```

4. Install the dependencies.
```
cd code
pip install -r requirements.txt
```
5. Copy the `.env.template` file into a new file named `.env` - this is where your API keys for your LLM and vector database of choice will go.

6. Add your LLM service API keys to the .env file.  

   If you want to use the Azure OpenAI service, follow the instructions in the [Azure Setup Guide](/docs/Azure.md).

> Note: By default, we assume you are using an Azure OAI endpoint and the 4.1, 4.1-mini, and text-embedding-3-small models.  If you are using a different setup, this needs to be changed in the [config_llm.yaml](code\config\config_llm.yaml) file. Make sure to set the following:
   > - Preferred Provider:  By default, this is `azure_openai` - replace this with your favorite provider listed within the file.
   > - Check your models:  For example, the default models for Azure OpenAI are 4.1 and 4.1-mini, but you may want to change these to 4o and 4o-mini.

7. Add your vector database keys to the .env file.

   If you want to use Snowflake services, follow the instructions at [docs/Snowflake.md](docs/Snowflake.md).

   If you would like to test with a local vector database, see below to [deploy](#deploying-a-local-database) and add [data](#loading-data-into-your-local-database) below.

8. Run a quick connectivity check:
```
python azure-connectivity.py     # If you'd like to use Azure as the LLM/retrieval provider.
python snowflake-connectivity.py # If you'd like to use Snowflake as the LLM/retrieval provider.
```

9. If you are participating in the private preview, modify your local copy of the [config_nlweb.yaml](code\config\config_nlweb.yaml) to scope the `sites` to search over your website only.

10. Run the application locally:
```
python app-file.py
```

11. Navigate to the local site and start your chat:
- You can also experiment at http://localhost:8000/ or http://localhost:8000/static/nlwebsearch.html 
- Try different modes / sites at http://localhost:8000/static/str_chat.html

   > Note: Your site scope was set above in the [config_nlweb.yaml](code\config\config_nlweb.yaml) file

## Deploying a Local Database


## Loading Data into your Local Database


## Deployment (CI/CD)

_At this time, the repository does not use continuous integration or produce a website, artifact, or anything deployed._

## Access

For questions about this GitHub project, please reach out to [NLWeb Support](mailto:NLWebSup@microsoft.com).

## Contributing

Please see [Contribution Guidance](CONTRIBUTING.md) for more information.

## License 

NLWeb uses the [MIT License](LICENSE).

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
