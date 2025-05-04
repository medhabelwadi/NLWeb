# Responsible AI FAQ

## What is NLWeb?

NLWeb, or ‘Natural Language Web,’ allows users to easily add natural language search to their websites, leveraging existing site schema data stored in a vectorized database, eliminating the need for advanced AI skills to implement.  This repo contains one possible 'default' implementation that can fit many search scenarios, leveraging Azure components - however, both the code and components are flexible and may be altered as desired based on the website environment and scenario needs. 

## What can NLWeb do? 

When a site uses NLWeb, the end-user is able to query the site to search in natural language and return relevant items from the site, which are ensured to exist because the database is based on their site contents (e.g., they are not LLM generated, but database entries). Tranditional keyword search is unable to understand the complex and potentially multi-turn queries for which NLWeb is able to quickly return relevant results.

## What is NLWeb’s intended use(s)?

NLWeb is intended to be used as a search mechanism across structured data on a website.  While the default implementation assumes we are using schema.org data, this is not required and customers could instead use, for example, their content catalog.

## How was NLWeb evaluated? What metrics are used to measure performance?

NLWeb was evaluated with a variety of prompts and techniques.  <TO DO: add testing information>

## What are the limitations of NLWeb? How can users minimize the impact of NLWeb’s limitations when using the system?

NLWeb requires structured data to search across, with this default implementation assuming a web schema in a vector database.  Initial queries are deliberatively generic and allow for common search patterns.  However, there are a few prompts containing specific examples of ways to make prompts more domain specific if there are particular search aspects the site wishes to emphasize/consider for their end-users.  

## What operational factors and settings allow for effective and responsible use of NLWeb?

While NLWeb has been evaluated for its resilience to prompt and data corpus injection attacks, and has been probed for specific types of harms, the LLM that the user calls with NLWeb may produce inappropriate or offensive content, which may make it inappropriate to deploy for sensitive contexts without additional mitigations that are specific to the use case and model. Developers should assess outputs for their context and use available safety classifiers, model specific safety filters and features (such as https://azure.microsoft.com/en-us/products/ai-services/ai-content-safety), or custom solutions appropriate for their use case.
