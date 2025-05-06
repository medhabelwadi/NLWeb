
Getting your NLWeb Server up and running locally on a Mac or Unix.

This will get you up and running, using the Azure AI Search vector database endpoint
that we have populated for you. You can replace that later with your own database.

1. Download the code from the repo.

2. Open a terminal, Create virtual python env and activate it.

3. Go to the root directory of the rep (you should see subdirectories like code and static) and
run pip install -r requirements.txt

4. create a file called .env and add the lines (for the variables AZURE_VECTOR_SEARCH_API_KEY
and AZURE_VECTOR_SEARCH_ENDPOINT) from the document sent to you via email

5. In the file code/config/config_llm.yaml, add your key for your favourite LLM. If is not azure_opeai, make sure you change the preferred_provider on the first line.

6. Edit code/config/config_nlweb and edit sites: to your site name (without www or .com suffix)

6. Go to the directory 'code' and run python app-file.py. Go to localhost:8000/


