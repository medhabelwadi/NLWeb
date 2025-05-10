"""
Check connectivity to Snowflake services.
Run this script to validate environment variables and API access.
"""


try:
    import asyncio
    import time
    import json
    from llm import snowflake
    from retrieval import snowflake_retrieve
    import sys
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

async def check_and_print(f) -> bool:
    try:
        result = await f()
        if result:
            print(f"✅ {f.__name__}")
        else:
            print(f"❌ {f.__name__}")
        return result
    except Exception as e:
        print(f"❌ {f.__name__}: {e}")
        return False

async def cortex_embed() -> bool:
    embedding = await snowflake.cortex_embed("Testing connectivity")
    return len(embedding) > 0

async def cortex_complete() -> bool:
    resp = await snowflake.cortex_complete("The answer to the ultimate question of life, the universe, and everything is", {"answer": "string"})
    return resp.get("answer", None) is not None

async def cortex_search() -> bool:
    resp = await snowflake_retrieve.search("funny movies", top_n=1)
    return len(resp) > 0 and len(resp[0]) == 4

async def main():
    """Run all connectivity checks"""

    start_time = time.time()
    tasks = [
        check_and_print(cortex_embed),
        check_and_print(cortex_complete),
        check_and_print(cortex_search),
    ]
    print("Running Snowflake connectivity checks...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful = sum(1 for r in results if r is True)
    total = len(tasks)
    
    print(f"\n====== SUMMARY ======")
    print(f"{successful}/{total} connections successful")
    if successful < total:
        print("❌ Some connections failed. Please check error messages above.")
    else:
        print("✅ All connections successful! Your environment is configured correctly.")
    elapsed_time = time.time() - start_time
    print(f"Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

