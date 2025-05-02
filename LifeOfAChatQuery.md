# Life of a chat query

1. User submits next query in the conversation

2. Multiple parallel calls are made for checking relevancy, decontextualizing query based on conversation history, determining if there are items that should be remembered in memory, etc. Each of these is implemented as a call to an LLM, though alternate implementations are possible. At the end of this, we have a decontextualized query, which we know is relevant to the site, that we have all the information required to answer the query, etc. In some cases, this step might result in the query being broken down into multiple smaller queries. In some cases, the system may return a response (e.g., when more information is required for further processing) and not go any further. 

3. The (decontextualized) query/queries is sent to a database service to retrieve potential answers. Typically, this is a vector database and the retrieval is a combination of tfidf scores on embeddings and structured data constraints. The data is returned as a set of json objects encoded in schema.org schema. 

4. The results returned from the database are scored. This is again done with a set of very specific calls to an LLM. The LLM may also be asked to generate a 'snippet' that is appropriate for the query. The top N results that have a score above some threshold, together with the score, snippet and the associated database object are collected.

5. If the user has requested post processing, this is done and the results from 4, together with the results from post processing are returned to the user. Post processing may for example summarize the results in 4 or go a step further and try to use the results from 4 to answer the query.

## Notes

- Processing a single query might involve over 50 LLM API calls. The calls tend to be very narrow and specific. Different kinds of calls may be to different models. The prompts can be specialized, declaratively, for particular object types (with the default type hierarchy from schema.org), e.g., Recipe vs Real Estate and further for specific sites.

- Since the items that are returned each come the database, the user can be assured that none of the results are 'made up'. There is of course the possibility that the results are not the best, but there will never be a result not in the database. Post processing may dilute this guarentee.

## Fast track

We expect that most conversations, especially early on, will resemble search and will involve a query that is releveant, doesn't require decontextualization, etc. So, it is very likely that step 2 will not make any changes to what follows. Consequently, after a light weight check to see if this condition might hold, a 'fast track' path to 3 is launched, in parallel to (2). Results from (4) are blocked from being sent to the user until the results of the analysis from (2) are completed. In some cases, the results from the fast track channel may be entirely dropped.