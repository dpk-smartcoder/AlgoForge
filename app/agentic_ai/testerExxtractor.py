import asyncio
import logging
import os
from dotenv import load_dotenv
from app.agentic_ai.extractor import ExtractorAgent
from app.agentic_ai.model_client import Model_Client

# Load environment variables from .env file
load_dotenv()

# Configure logging to show detailed output for debugging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Main execution ---
async def main():
    # Load model configuration from environment variables
    model = os.getenv("extraction_model")
    api_key = os.getenv("extraction_key")

    if not model or not api_key:
        logging.error("FATAL: 'extraction_model' or 'extraction_key' not found in environment variables.")
        return

    logging.info(f"Using model: {model}")

    # Initialize the model client and the ExtractorAgent
    try:
        model_client = Model_Client(model, API_KEY=api_key).getClient()
        agent = ExtractorAgent(llm_client=model_client)
    except Exception as e:
        logging.error(f"Failed to initialize clients: {e}")
        return

#     --- Test Cases ---

    print("\n=== Test 1: Only Text Input ===")
    try:
        # The `run` method is the new entry point for all tasks.
        result1 = await agent.extract_text(text="""
Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays.

The overall run time complexity should be O(log (m+n)).

Example 1:
Input: nums1 = [1,3], nums2 = [2]
Output: 2.00000
Explanation: merged array = [1,2,3] and median is 2.

Example 2:
Input: nums1 = [1,2], nums2 = [3,4]
Output: 2.50000
Explanation: merged array = [1,2,3,4] and median is (2 + 3) / 2 = 2.5.

Constraints:
nums1.length == m
nums2.length == n
0 <= m <= 1000
0 <= n <= 1000
1 <= m + n <= 2000
-106 <= nums1[i], nums2[i] <= 106
""")
        logging.info(f"Test 1 Result: {result1}")
    except Exception as e:
        logging.error(f"Test 1 failed: {e}")


    print("\n=== Test 2: Only Image Input ===")
    # IMPORTANT: Replace these with actual paths to images on your computer.
    # image_files_test_2 = ["Screenshot 2025-08-13 at 7.48.43 AM.png", "Screenshot 2025-08-13 at 7.49.00 AM.png"]
    # try:
    #     # Pass images as a list to the `images` parameter.
    #     result2 = await agent.run(images=image_files_test_2)
    #     logging.info(f"Test 2 Result: {result2}")
    # except Exception as e:
    #     logging.error(f"Test 2 failed: {e}. Make sure your image paths are correct.")


#     print("\n=== Test 3: Image + Text Input ===")
#     # IMPORTANT: Replace this with an actual path to an image on your computer.
#     image_file_test_3 = ["path/to/your/image3.png"]
#     text_test_3 = """
# Please extract the constraints from the attached image.
# Constraints:
# nums1.length == m
# nums2.length == n
# 0 <= m <= 1000
# 0 <= n <= 1000
# 1 <= m + n <= 2000
# -106 <= nums1[i], nums2[i] <= 106
# """
#     try:
#         # Pass both image and text to the `run` method.
#         result3 = await agent.run(images=image_file_test_3, user_text=text_test_3)
#         logging.info(f"Test 3 Result: {result3}")
#     except Exception as e:
#         logging.error(f"Test 3 failed: {e}. Make sure your image path is correct.")


if __name__ == "__main__":
    asyncio.run(main())