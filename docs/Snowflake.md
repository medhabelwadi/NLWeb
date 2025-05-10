# Snowflake

The Snowflake AI Data Cloud provides:
* Various [LLM functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-llm-rest-api) and
* And [interactive search over unstructured data](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview)

This guide walks you through how to use LLMs available in your Snowflake account.

## Connect to your Snowflake account

The sample application can use a [programmatic access token](https://docs.snowflake.com/en/user-guide/programmatic-access-tokens)

1. Login to your Snowflake account, e.g., https://<account_identifier>.snowflakecomputing.com/
2. Click on your user, then "Settings", then "Authentication"
3. Under "Programmatic access tokens" click "Generate new token"
4. Set `SNOWFLAKE_ACCOUNT_URL` and `SNOWFLAKE_PAT` in the `.env` file (as [README.md](../README.md) suggests
5. (Optionally): Set `SNOWFLAKE_EMBEDDING_MODEL` to an [embedding model available in Snowflake](https://docs.snowflake.com/en/user-guide/snowflake-cortex/vector-embeddings#text-embedding-models)

## Test connectivity

Run:

```
python snowflake-connectivity.py
```

If configuration is set correctly, you'll see something like: `✅ All connections successful!`

## Use LLMs from Snowflake

1. Edit [config_llm.yaml](../code/config_llm.yaml) and change `preferred_provider` at the top to `preferred_provider: snowflake`
2. (Optionally) adjust the models to use by setting `snowflake.models.high` or `snowflake.models.low` in `config_llm.yaml` to any of [the models available to your Snowflake account](https://docs.snowflake.com/en/user-guide/snowflake-cortex/llm-functions#availability), and/or
