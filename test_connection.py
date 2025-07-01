import requests
import ssl
import certifi
import sys

def test_connection():
    print("Testing SSL and network configuration...")
    
    try:
        # Test SSL context
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        print("SSL Context created successfully")
        
        # Test connection to Gemini API
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        response = requests.get(url, verify=certifi.where())
        print(f"Connection test status code: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    if test_connection():
        print("Connection test passed!")
    else:
        print("Connection test failed!")
        print("\nTroubleshooting steps:")
        print("1. Check your internet connection")
        print("2. Verify you're not behind a restrictive firewall")
        print("3. Update your SSL certificates:")
        print("   pip install --upgrade certifi")
        print("4. If using a proxy, set the environment variables:")
        print("   HTTPS_PROXY=your_proxy_url")
        print("   HTTP_PROXY=your_proxy_url")