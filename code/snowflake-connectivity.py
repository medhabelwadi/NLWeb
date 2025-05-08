"""
Check connectivity to Snowflake services.
Run this script to validate environment variables and API access.
"""


try:
    import asyncio
    import time
    import json
    from llm import snowflake
    import sys
except ImportError as e:
    print(f"Error importing required libraries: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)


async def check_cortex_embed() -> bool:
    embedding = await snowflake.cortex_embed("Testing connectivity")
    return len(embedding) > 0

async def check_cortex_complete() -> bool:
    resp = await snowflake.cortex_complete("The answer to the ultimate question of life, the universe, and everything is", {"answer": "string"})
    return resp.get("answer", None) is not None

async def main():
    """Run all connectivity checks"""

    start_time = time.time()
    tasks = [
        check_cortex_embed(),
        check_cortex_complete(),
    ]
    print("Running Snowflake connectivity checks...")
    results = await asyncio.gather(*tasks, return_exceptions=False)
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

