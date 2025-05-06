
** Getting your NLWeb Server up and running **

This will get you up and running, using the Azure AI Search vector database endpoint
that we have populated for you. You can replace that later with your own database.

1. Download the code from the repo.
2. Create virtual python env and activate it.
3. pip install -r requirements.txt
5. edit config_retrieval.yaml to point at the NLWeb_Crawl Azure AI search endpoint
4. create a file called set-keys.sh and add env variables with values of keys
   a. for LLM
   b. for azure ai search read only
6. Edit config_nlweb and add site: eventbrite
6. python app-file.py. Go to localhost:8000/


