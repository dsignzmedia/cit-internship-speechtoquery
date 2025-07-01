from sql_generator import SQLGenerator
import os
from dotenv import load_dotenv
import sys

def verify_environment():
    """Verify environment setup"""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found in .env file")
        print("Please make sure you have:")
        print("1. Created a .env file in the project directory")
        print("2. Added your OpenAI API key like this: OPENAI_API_KEY=your_key_here")
        print("\nTo get an API key:")
        print("1. Go to https://platform.openai.com/account/api-keys")
        print("2. Create a new API key or copy your existing one")
        print("3. Add it to your .env file")
        return False
        
    return True

def main():
    # Verify environment first
    if not verify_environment():
        return
        
    try:
        # Initialize the converter
        print("Initializing SQL Generator...")
        print("This may take a moment as we verify the API connection...")
        generator = SQLGenerator()
        
        # Example queries to test
        test_queries = [
            "I want to visit Maui and like to surf. Please recommend resorts near beaches that are good for surfing"
        ]
        
        # Test each query
        for text in test_queries:
            print("\nProcessing query:", text)
            result = generator.generate_query(text)
            
            if result["success"]:
                print("\nGenerated SQL:")
                print(result["query"])
            else:
                print("\nError:", result["error"])
            print("Timestamp:", result["timestamp"])
            print("-" * 80)
            
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Verify your API key is correct and active")
        print("2. Make sure you have internet connectivity")
        print("3. Try updating the packages:")
        print("   pip install --upgrade openai")
        print("4. If the error persists, try creating a new API key")

if __name__ == "__main__":
    main()
