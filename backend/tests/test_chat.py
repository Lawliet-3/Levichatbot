import requests
import json

def test_chat_endpoint():
    """Test the chat endpoint with various queries"""
    base_url = "http://localhost:8000"
    
    test_queries = [
        "Tell me about 501 jeans",
        "What denim jackets do you have?",
        "Show me slim fit jeans",
        "What's the difference between 501 and 511?",
        "Do you have any black jeans?"
    ]
    
    print("Testing Chat Endpoint...")
    print("-" * 50)
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        try:
            response = requests.post(
                f"{base_url}/api/chat/query",
                json={"query": query}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\nResponse:")
                print(result["response"])
                print("\nNumber of products retrieved:", len(result.get("products", [])))
                print("-" * 50)
            else:
                print(f"Error: Status code {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"Error making request: {str(e)}")

if __name__ == "__main__":
    test_chat_endpoint()