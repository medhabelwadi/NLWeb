import asyncio
import time
from config.config import CONFIG
from core.baseHandler import NLWebHandler
import yaml
import os
import dotenv
import statistics
import json
import matplotlib.pyplot as plt
import pandas as pd
from utils.utils import siteToItemType

# Load env variables and config
dotenv.load_dotenv()
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/config_llm.yaml'))

def load_conversations(path):
    """Load conversations from a JSONL file."""
    conversations = []
    with open(path, "r") as f:
        for line in f:
            obj = json.loads(line)
            conversations.append(obj["conversation"])
    return conversations

# Configuration
PROVIDERS = ["openai", "inception", "anthropic"]  # Choose providers to benchmark
RUN_SINGLE_TURN = True                  # Whether to run single-turn benchmark
RUN_MULTI_TURN = True                   # Whether to run multi-turn benchmark

# Load conversations
MULTITURN_CONVERSATIONS = load_conversations("./benchmark/data/conversations.jsonl")

def load_model_configs(config_path):
    """Load all provider pairs from config_llm.yaml."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    providers = config.get('providers', {})
    model_configs = []
    for provider, pdata in providers.items():
        model_configs.append({
            'provider': provider,
        })
    return model_configs

def is_valid_config(config):
    """Return True if provider config should be benchmarked."""
    return config['provider'] in PROVIDERS

async def single_turn(provider, query, generate_mode, streaming, query_id):
    """Run a single turn and return result, elapsed time, and error."""
    site = "scifi_movies"
    query_params = {
        "site": [site],
        "query": [query],
        "provider": [provider],
        "streaming": [str(streaming)],
        "generate_mode": [generate_mode],
        "query_id": [query_id]
    }
    handler = NLWebHandler(query_params, http_handler=None)
    start = time.time()
    try:
        result = await handler.runQuery()
        end = time.time()
        return result, end - start, None
    except Exception as e:
        end = time.time()
        return None, None, str(e)

def print_single_turn_stats_by_provider(all_results):
    """Print timing stats for single-turn results by provider."""
    from collections import defaultdict
    provider_times = defaultdict(list)
    for r in all_results:
        provider = r['provider']
        provider_times[provider].extend([t for t in r['times'] if t is not None])
    print("\n=== Single-turn Timing Stats by Provider ===")
    for provider, times in provider_times.items():
        if not times:
            print(f"Provider: {provider} - No successful timings.")
            continue
        print(f"Provider: {provider}")
        print(f"  Count: {len(times)}")
        print(f"  Min: {min(times):.3f} s")
        print(f"  Max: {max(times):.3f} s")
        print(f"  Mean: {statistics.mean(times):.3f} s")
        print(f"  Median: {statistics.median(times):.3f} s")
        print(f"  Stddev: {statistics.stdev(times):.3f} s" if len(times) > 1 else "  Stddev: N/A")

def print_multiturn_stats_by_provider(multiturn_results):
    """Print timing stats for multi-turn results by provider."""
    from collections import defaultdict
    provider_times = defaultdict(list)
    for r in multiturn_results:
        if r['turn'] != 'ALL' and r['elapsed'] is not None:
            provider = r['provider']
            provider_times[provider].append(r['elapsed'])
    print("\n=== Multi-turn (per turn) Timing Stats by Provider ===")
    for provider, times in provider_times.items():
        if not times:
            print(f"Provider: {provider} - No successful timings.")
            continue
        print(f"Provider: {provider}")
        print(f"  Count: {len(times)}")
        print(f"  Min: {min(times):.3f} s")
        print(f"  Max: {max(times):.3f} s")
        print(f"  Mean: {statistics.mean(times):.3f} s")
        print(f"  Median: {statistics.median(times):.3f} s")
        print(f"  Stddev: {statistics.stdev(times):.3f} s" if len(times) > 1 else "  Stddev: N/A")

def print_multiturn_conversation_stats_by_provider(multiturn_results):
    """Print timing stats for multi-turn conversation results by provider."""
    from collections import defaultdict
    provider_times = defaultdict(list)
    for r in multiturn_results:
        if r['turn'] == 'ALL' and r['elapsed'] is not None:
            provider = r['provider']
            provider_times[provider].append(r['elapsed'])
    print("\n=== Multi-turn (total conversation) Timing Stats by Provider ===")
    for provider, times in provider_times.items():
        if not times:
            print(f"Provider: {provider} - No successful timings.")
            continue
        print(f"Provider: {provider}")
        print(f"  Count: {len(times)}")
        print(f"  Min: {min(times):.3f} s")
        print(f"  Max: {max(times):.3f} s")
        print(f"  Mean: {statistics.mean(times):.3f} s")
        print(f"  Median: {statistics.median(times):.3f} s")
        print(f"  Stddev: {statistics.stdev(times):.3f} s" if len(times) > 1 else "  Stddev: N/A")

async def run_single_turn_benchmark(model_configs, generate_mode, streaming, num_runs=1):
    """Run single-turn benchmark and return results."""
    all_results = []
    for conversation in MULTITURN_CONVERSATIONS:
        query = conversation[0]
        print(f"\n=== Benchmarking for query: {query} ===")
        results = []
        for config in model_configs:
            if not is_valid_config(config):
                continue
            provider = config['provider']
            CONFIG.preferred_provider = provider
            times = []
            errors = []
            print(f"Provider: {provider}")
            for i in range(num_runs):
                query_id = f"benchmark_{query}_{provider}_{i}"
                result, elapsed, error = await single_turn(provider, query, generate_mode, streaming, query_id)
                if error is None:
                    print(f"    Run {i+1}: {elapsed:.3f} seconds")
                    times.append(elapsed)
                    errors.append(None)
                else:
                    print(f"    Run {i+1}: ERROR - {error}")
                    times.append(None)
                    errors.append(error)
            valid_times = [t for t in times if t is not None]
            avg_time = sum(valid_times) / len(valid_times) if valid_times else None
            results.append({
                'query': query,
                'provider': provider,
                'times': times,
                'errors': errors,
                'avg_time': avg_time
            })
        all_results.extend(results)
    return all_results

async def run_multiturn_benchmark(model_configs, generate_mode, streaming):
    """Run multi-turn benchmark and return results."""
    multiturn_results = []
    for config in model_configs:
        if not is_valid_config(config):
            continue
        provider = config['provider']
        CONFIG.preferred_provider = provider
        for conv_idx, conversation in enumerate(MULTITURN_CONVERSATIONS):
            print(f"\n--- Conversation {conv_idx+1} | Provider: {provider} ---")
            site = "scifi_movies"
            handler = NLWebHandler({
                "site": [site],
                "provider": [provider],
                "streaming": [str(streaming)],
                "generate_mode": [generate_mode],
                "query_id": [f"multiturn_{conv_idx}_0_{provider}"],
                "prev": []
            }, http_handler=None)
            handler.site = site
            conv_start = time.time()
            conversation_log = []  # Collect (query, answer) pairs
            handler.prev_answers = []  # Add prev_answers attribute for multi-turn
            for turn_idx, user_query in enumerate(conversation):
                print(f"\nTurn {turn_idx+1}: '{user_query}'")
                handler.query = user_query
                handler.query_id = f"multiturn_{conv_idx}_{turn_idx}_{provider}"
                if turn_idx == 0:
                    handler.prev_queries = []
                    handler.prev_answers = []
                try:
                    handler.item_type = siteToItemType(site)    
                    start = time.time()
                    result = await handler.runQuery()
                    if result.get('summary') is None:
                        raise Exception("No summary found")
                    elapsed = time.time() - start
                    print(f"  Turn {turn_idx+1}: {elapsed:.3f} seconds")
                    conversation_log.append({'query': user_query, 'answer': result['summary']['message']})
                    multiturn_result = {
                        'conversation': conv_idx+1,
                        'turn': turn_idx+1,
                        'provider': provider,
                        'elapsed': elapsed,
                        'answer': result['summary']['message'],
                        'error': None,
                        'query': user_query,
                        'conversation_log': conversation_log.copy()
                    }
                    multiturn_results.append(multiturn_result)
                    handler.prev_answers.append(result)
                except Exception as e:
                    elapsed = None
                    print(f"  Turn {turn_idx+1}: ERROR: {e}")
                    conversation_log.append({'query': user_query, 'answer': str(e)})
                    multiturn_result = {
                        'conversation': conv_idx+1,
                        'turn': turn_idx+1,
                        'provider': provider,
                        'elapsed': None,
                        'error': str(e),
                        'query': user_query,
                        'conversation_log': conversation_log.copy()
                    }
                    multiturn_results.append(multiturn_result)
                    handler.prev_answers.append(str(e))
                handler.prev_queries.append(user_query)
            conv_end = time.time()
            total_conv_time = conv_end - conv_start
            print(f"Total time for conversation {conv_idx+1} ({provider}): {total_conv_time:.3f} seconds")
            multiturn_results.append({
                'conversation': conv_idx+1,
                'turn': 'ALL',
                'provider': provider,
                'elapsed': total_conv_time,
                'error': None,
                'query': 'TOTAL_CONVERSATION_TIME',
                'conversation_log': conversation_log.copy()
            })
    return multiturn_results

def plot_results(results, title, filename):
    """Plot results and save to file."""
    df = pd.DataFrame(results)
    df = df[df['elapsed'].notnull()]
    if df.empty:
        print(f"No successful results to plot for {title}.")
        return
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    df.boxplot(column='elapsed', by=['provider'], ax=ax)
    plt.title(title)
    plt.suptitle("")
    plt.ylabel('Elapsed Time (s)')
    plt.xlabel('Provider')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(filename)
    plt.show()

def plot_total_conversation_time_per_provider(results, title, filename):
    """Plot total conversation time per provider and save to file."""
    df = pd.DataFrame(results)
    df = df[(df['elapsed'].notnull()) & (df['turn'] == 'ALL')]
    if df.empty:
        print(f"No successful results to plot for {title}.")
        return
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    df.boxplot(column='elapsed', by=['provider'], ax=ax)
    plt.title(title)
    plt.suptitle("")
    plt.ylabel('Total Conversation Time (s)')
    plt.xlabel('Provider')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(filename)
    plt.show()

async def run_benchmark():
    """Main entry point for running benchmarks and reporting results."""
    model_configs = load_model_configs(CONFIG_PATH)
    generate_mode = "summarize"
    streaming = False
    num_runs = 1

    if RUN_SINGLE_TURN:
        all_results = await run_single_turn_benchmark(model_configs, generate_mode, streaming, num_runs)
        with open('../data/benchmark_results/single_turn_results.json', 'w') as f:
            json.dump(all_results, f, indent=2)
        print_single_turn_stats_by_provider(all_results)
        plot_results(
            [
                {'provider': r['provider'], 'elapsed': t}
                for r in all_results for t in r['times'] if t is not None
            ],
            title='Single-turn Benchmark Timing by Provider',
            filename='../data/benchmark_results/single_turn_benchmark.png'
        )
    if RUN_MULTI_TURN:
        multiturn_results = await run_multiturn_benchmark(model_configs, generate_mode, streaming)
        with open('../data/benchmark_results/multiturn_results.json', 'w') as f:
            json.dump(multiturn_results, f, indent=2)
        print_multiturn_stats_by_provider(multiturn_results)
        print_multiturn_conversation_stats_by_provider(multiturn_results)
        plot_results(
            [r for r in multiturn_results if r['turn'] != 'ALL'],
            title='Multi-turn Benchmark Timing by Provider',
            filename='./benchmark/data/results/multiturn_benchmark.png'
        )
        plot_total_conversation_time_per_provider(
            multiturn_results,
            title='Total Conversation Time by Provider',
            filename='./benchmark/data/results/multiturn_total_conversation_time.png'
        )

if __name__ == "__main__":
    asyncio.run(run_benchmark())