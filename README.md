# What is NLWeb

NLWeb aims to make it simple to provide conversational interfaces to
websites (or more generally, collections of content) which can be abstracted
as 'lists of items'. Items maybe recipes, events, products, books, movies, etc.
NLWeb leverages the fact that most such database driven websites already make their data
available in a structured form, in a common vocabulary, namely that provided
by Schema.org. We leverage this to make it easy to create conversational interfaces.

Given a database of items, represented in a semi-structured form, NLWeb 
provides a RESTful conversational natural language interface to this data.
In its basic mode, NLWeb will return a subset of the list of items in the
database. Consequently strong assurances can be made that it will not 'make up'
items that don't exist, an essential requirement for many applications.

NLWeb is deeply agnostic:
- About the platform. We have tested it running on Windows, MacOS, Linux, Azure ...
- About the vector stores used --- Qdrant, Snowflake, Milvus, Azure AI Search, ...
- About the LLM --- OAI, Deepseek, Gemini, Anthropic, InceptionLabs, ...
- It is intended to be both lightweight and scalable, running on everything from clusters 
  in the cloud to laptops and soon phones.

# How it Works
 At a high level, NLWeb follows the pattern used in modern search engines --- a retrieval
 process involving relatively cheap ranking (in our case, with embeddings in vector
 databases) followed by 'deeper' ranking (in our ase, with llms). It does not use
 'traditional' RAG which can sometime hallucinate. More on how it works is here.

# NLWeb and MCP

# Repository
This repository contains the following:

- the code for the core service -- handling a natural language query. See below for documentation
  on how this can be extended / customized
- connectors to some of the popular LLMs and vector databases. See documentation on how to add more.
- tools for adding data in schema.org jsonl, RSS, etc. to a vector databaes of choice
- a web server front end for this service, which being small enough runs in the web server
- a simple UI for enabling users to issue queries via this web server

We expect most production deployments to use their own UI. They are also likely to integrate
the code into their application environment (as opposed to running a standalone NLWeb server).


# Documentation

## Getting Started
- Hello world on your laptop
- Running it on Azure
- Running it on GCP ... coming soon
- Running it AWS ... coming soon

## Connecting
- Adding a new LLM provider
- Adding a new Vector store connector

## NLWeb
- Life of a Chat Query
- Modifying behaviour by changing prompts
- Modifying control flow



-----------------------------------------------------------------

## License 

NLWeb uses the [MIT License](LICENSE).


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
