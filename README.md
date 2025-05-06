# Project


# NLWeb

Add LLM chat functionality to your existing web pages by leveraging your site schema

-----------------------------------------------------------------

## License 

NLWeb uses the [MIT License](LICENSE).


## Getting Started

Use these instructions to run an NLWeb server locally (for demo or test purposes)

### Prerequisites

These instructions assume you have the ability to clone/download a GitHub repo, and have Python installed in your IDE.


### Installing

Install and Running Webapp Locally

1. Clone or download repository.

2. Install dependencies:

  - Create a virtual environment (if you don't have one), replacing 'myenv' with the name you want to give your environment
```
python3 -m venv myenv
```

  - Activate the virtual environment - again, replace 'myenv' with the name you selected above 
```
source myenv/bin/activate
```

  - Install requirements
```
cd ~/NLWEB/webapp
pip install -r requirements.txt
```

3. Setup your service api-keys:
Create a new file named `set-keys.sh` in the webapp folder (you'll find an example file as 'example-set-key.sh').  You'll then add the endpoints and APIs in this file as written below.

For instructions on obtaining the required Azure service keys, see [this guide on retrieving Azure credentials](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/keys) or refer to the [Azure Search example](https://learn.microsoft.com/en-us/azure/search/search-security-api-keys) for step-by-step details.
```
export AZURE_VECTOR_SEARCH_ENDPOINT=" " 
export AZURE_VECTOR_SEARCH_API_KEY="your key"
export AZURE_OPENAI_ENDPOINT=" "
export AZURE_OPENAI_API_KEY="your key"
```

- Set your local environment to run with your service keys:

```
source set-keys.sh
```

4. Run your webapp server: 
```
python app-file.py
```

6. Navigate to the local site and start your chat:
```
(http://localhost:8000/html/str_chat.html)
```

## Tests

To test your variables are correctly set to connect to Azure, see azure-connectivity.py


## Deployment (CI/CD)

_At this time, the repository does not use continuous integration or produce a website, artifact, or anything deployed._

## Access

For questions about this GitHub project, please reach out to [NLWeb Support](mailto:NLWebSup@microsoft.com).

## Contributing

Please see [Contribution Guidance](CONTRIBUTING.md) for more information.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
