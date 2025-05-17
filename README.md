# What is NLWeb


Building conversational interfaces for websites is hard. NLWeb seeks to make it easy. 
Built on MCP, it offers protocols and tools that enable websites to create agent endpoints, 
fostering a web of interoperating agents. NLWeb's main focus is establishing a foundational 
protocol layer for the AI Web — much like HTML revolutionized document sharing and RSS 
transformed content syndication. We're creating standardized protocols and formats that 
unlock new functionality and interoperability, fostering more dynamic and equitable digital 
ecosystems. Building on Schema.org's success as the web's de facto semantic layer (adopted 
by over 100 million sites), NLWeb creates an additional semantic layer specifically 
designed for AI agent interactions via MCP. NLWeb benefits both humans and machines: 
it gives website users conversational interfaces while enabling agents to interact 
naturally with each other, creating a web of connected agents.

To make this vision reality, NLWeb provides practical implementation code—not as the 
definitive solution, but as proof-of-concept demonstrations showing one possible 
approach. We expect and encourage the community to develop diverse, innovative 
implementations that surpass our examples. This mirrors the web's own evolution, 
from the humble 'htdocs' folder in NCSA's http server to today's massive data center 
infrastructures—all unified by shared protocols that enable seamless communication.

AI has the potential to enhance every web interaction, but realizing this vision 
requires a collaborative effort reminiscent of the web's early "barn raising" spirit. 
Success demands shared protocols, sample implementations, and community participation. 
NLWeb combines protocols, Schema.org formats, and sample code to help sites rapidly 
create these endpoints, benefiting both humans through conversational interfaces and 
machines through natural agent-to-agent interaction. Join us in building this connected web of agents.


# How it Works
 There are two distinct components to NLWeb.
 1. A protocol, very simple to begin with, to interface with a site in natural 
     language for asking a site's and a format, leveraging json and schema.org 
     for the returned answer. See the documentation on the REST API for more details.

 2. A straightforward implementation of (1) that leverages existing markup, for
      sites that can be abstracted as lists of items (products, recipes, attractions,
      reviews, etc.). Together with a set of user interface widgets, sites can 
      easily provide conversational interfaces to their content. See the documentation
      on [Life of a chat query](docs/LifeOfAChatQuery.md) for more details on how this works.


# NLWeb and MCP
 MCP (Model Context Protocol) is an emerging protocol for Chatbots and AI assistants
 to interact with tools. Every NLWeb instance is also an MCP server, which supports one method,
 <code>ask</code>, which is used to ask a website a question in natural language. The returned response
 leverages schema.org, a widely-used vocabulary for describing web data. Loosely speaking, 
 MCP is NLWeb as Http is to HTML.


# NLWeb and platforms.
NLWeb is deeply agnostic:
- About the platform. We have tested it running on Windows, MacOS, Linux, ...
- About the vector stores used: Qdrant, Snowflake, Milvus, Azure AI Search, ...
- About the LLM: OAI, Deepseek, Gemini, Anthropic, Inception, ...
- It is intended to be both lightweight and scalable, running on everything from clusters 
  in the cloud to laptops and soon phones.


# Repository
This repository contains the following:

- the code for the core service -- handling a natural language query. See below for documentation
  on how this can be extended / customized
- connectors to some of the popular LLMs and vector databases. See documentation on how to add more.
- tools for adding data in schema.org jsonl, RSS, etc. to a vector database of choice
- a web server front end for this service, which being small enough runs in the web server
- a simple UI for enabling users to issue queries via this web server

We expect most production deployments to use their own UI. They are also likely to integrate
the code into their application environment (as opposed to running a standalone NLWeb server). They
are also encouraged to connect NLWeb to their 'live' database as opposed to copying
the contents over, which inevitably introduces freshness issues.


# Documentation

## Getting Started
- [Hello world on your laptop](HelloWorld.md)
- [Running it on Azure](docs/Azure.md)
- Running it on GCP ... coming soon
- Running it AWS ... coming soon

## NLWeb
- [Life of a Chat Query](docs/LifeOfAChatQuery.md)
- [Modifying behaviour by changing prompts](docs/Prompts.md)
- [Modifying control flow](docs/ControlFlow.md)
- Modifying the user interface
- [REST interface](docs/RestAPI.md)



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
