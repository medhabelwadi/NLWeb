import os
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, AuthenticationError

# Load environment variables (just in case)
load_dotenv()

# Get the API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY environment variable not found.")
    exit(1)

print(f"Attempting connection with API Key: {api_key[:5]}...{api_key[-5:]}")

try:
    # Initialize the OpenAI client directly
    client = OpenAI(api_key=api_key)

    # Make a simple chat completion call
    print("Making a test chat completion request...")
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo", # Use a common, affordable model like gpt-3.5-turbo
        messages=[{"role": "user", "content": "Say hello!"}],
        max_tokens=10
    )
    print("Chat completion successful!")
    print(f"Response: {chat_completion.choices[0].message.content}")

    # Make a simple embedding call
    print("\nMaking a test embedding request...")
    embedding_response = client.embeddings.create(
        input="This is a test sentence.",
        model="text-embedding-3-small" # Use a common, affordable embedding model
    )
    print("Embedding generation successful!")
    # print(f"Embedding: {embedding_response.data[0].embedding[:5]}...") # Uncomment to see part of the embedding

except AuthenticationError as e:
    print(f"\nAuthentication Error: {e}")
    print("This means the API key is incorrect or has an issue. Double-check on platform.openai.com/account/api-keys")
except APIConnectionError as e:
    print(f"\nConnection Error: {e}")
    print("This means there's a network issue preventing connection to OpenAI. Check firewall/VPN.")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")