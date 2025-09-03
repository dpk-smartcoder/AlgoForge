import asyncio
import os
from dotenv import load_dotenv
from extractor import ExtractorAgent
from model_client import Model_Client

# --- Configuration ---

# Load environment variables from a .env file
load_dotenv()

# IMPORTANT: Store your API key in a .env file for security.
# Create a file named .env in the same directory and add the line:
# API_KEY_MODEL4="your_actual_api_key_here"
API_KEY = "AIzaSyDfysUaCe6dqrlx_Po7A1xpPT1vQrsQtGA"
MODEL_NAME = "gemini-2.0-flash" 

# --- Main Execution Logic ---

async def main():
    """
    Initializes and runs the ExtractorAgent to process images and text.
    """
    if not API_KEY:
        print("Error: API_KEY_MODEL4 not found in environment variables.")
        print("Please create a .env file and add your API key.")
        return

    # Initialize the LLM client with the model and API key
    llm_client = Model_Client(model=MODEL_NAME, API_KEY=API_KEY).getClient()

    # Create an instance of the ExtractorAgent
    extractor = ExtractorAgent(llm_client=llm_client)

    # --- Input Data ---

    # IMPORTANT: Make sure these image files are in the same directory as this script,
    # or provide the full path to each file.
    image_paths = [
        "1.png",
        "2.png",
        "3.png"
    ]

    problem_text = """
You are given an integer array order of length n and an integer array friends.

order contains every integer from 1 to n exactly once, representing the IDs of the participants of a race in their finishing order.
friends contains the IDs of your friends in the race sorted in strictly increasing order. Each ID in friends is guaranteed to appear in the order array.
Return an array containing your friends' IDs in their finishing order.

Example 1:

Input: order = [3,1,2,5,4], friends = [1,3,4]

Output: [3,1,4]

Explanation:

The finishing order is [3, 1, 2, 5, 4]. Therefore, the finishing order of your friends is [3, 1, 4].

Example 2:

Input: order = [1,4,5,3,2], friends = [2,5]

Output: [5,2]

Explanation:

The finishing order is [1, 4, 5, 3, 2]. Therefore, the finishing order of your friends is [5, 2].

Constraints:

1 <= n == order.length <= 100
order contains every integer from 1 to n exactly once
1 <= friends.length <= min(8, n)
1 <= friends[i] <= n
friends is strictly increasing


class Solution {
    public int[] recoverOrder(int[] order, int[] friends) {
        
    }
}
"""
    
    # --- Run the Extraction ---
    
    print("Starting extraction process with images and text...")
    try:
        # Await the asynchronous extract_image method
        await extractor.extract_image(image_paths, problem_text)
        print("\nExtraction process finished successfully!")
        print("Check for a 'data.json' file in your directory for the results.")
    except Exception as e:
        print(f"\nAn error occurred during extraction: {e}")


if __name__ == "__main__":
    # This runs the main asynchronous function
    asyncio.run(main())
