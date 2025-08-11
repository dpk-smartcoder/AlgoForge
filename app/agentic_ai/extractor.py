from autogen_agentchat.agents import AssistantAgent
from dotenv import load_dotenv
load_dotenv()
import os
import json
import asyncio
import logging

MAX_IMAGES = 3
LLM_TIMEOUT = 30
MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)

ex_prompt=os.getenv("extract_prompt")
vr_prompt=os.getenv("verify_prompt")
class ExtractorAgent():
    def __init__(self,llm_client):
        self.llm=AssistantAgent(
            name="Extractor",
            description="Will extract data from user input",
            system_message=ex_prompt,
            model_client=llm_client
        )
        self.verifier=AssistantAgent(
            name="Verifier",
            description="Will Verify data from Extractor input",
            system_message=vr_prompt,
            model_client=llm_client
        )
    
    async def _call_llm_with_timeout(self, payload):
        try:
            logger.debug(f"Calling LLM with payload: {payload}")
            result = await asyncio.wait_for(self.llm.run(payload), timeout=LLM_TIMEOUT)
            logger.debug(f"LLM returned: {result}")
            return result
        except asyncio.TimeoutError:
            logger.error("LLM call timed out")
            raise
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def extract_image(self, image):
        if image is None:
            logger.warning("No image provided to extract_image")
            return
        images = image if isinstance(image, list) else [image]
        if not (1 <= len(images) <= MAX_IMAGES):
            raise ValueError(f"Number of images must be between 1 and {MAX_IMAGES}, got {len(images)}")
        logger.info(f"Extracting from {len(images)} image(s)")
        try:
            tasks = [self._call_llm_with_timeout(img) for img in images]
            results = await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error during image extraction: {e}")
            raise
        combined_text = "\n---\n".join(results)
        await self.extract_text(combined_text)

    async def extract_text(self, text):
        prompt = text
        for attempt in range(1, MAX_ATTEMPTS + 1):
            logger.info(f"Extraction attempt {attempt}")
            try:
                extracted = await self._call_llm_with_timeout(prompt)
                # Try parse as JSON
                try:
                    extracted_json = json.loads(extracted)
                except json.JSONDecodeError:
                    # Re-prompt LLM to convert to JSON
                    convert_prompt = f"Please convert the following text to valid JSON:\n{extracted}"
                    logger.debug("Attempting to convert extracted text to JSON via LLM")
                    extracted_json_str = await self._call_llm_with_timeout(convert_prompt)
                    try:
                        extracted_json = json.loads(extracted_json_str)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON after conversion attempt")
                        extracted_json = None
                if extracted_json is None:
                    verification_input = extracted
                else:
                    verification_input = json.dumps(extracted_json)
                try:
                    verification_output = await asyncio.wait_for(self.verifier.run(verification_input), timeout=LLM_TIMEOUT)
                    logger.debug(f"Verifier output: {verification_output}")
                except asyncio.TimeoutError:
                    logger.error("Verifier call timed out")
                    raise
                except Exception as e:
                    logger.error(f"Verifier call failed: {e}")
                    raise
                # Interpret verifier output
                verified = False
                try:
                    # Attempt parse as JSON with a 'verified' field
                    verifier_json = json.loads(verification_output)
                    if isinstance(verifier_json, dict):
                        verified = verifier_json.get("verified", False) is True
                except json.JSONDecodeError:
                    # fallback to yes/no style
                    if verification_output.strip().lower() in ['yes', 'true', 'correct', 'valid', 'verified']:
                        verified = True
                if verified:
                    with open("data.json", "w") as f:
                        if extracted_json is not None:
                            json.dump(extracted_json, f)
                        else:
                            f.write(extracted)
                    logger.info("Extraction and verification successful, data saved")
                    return
                else:
                    logger.warning(f"Verification failed on attempt {attempt}: {verification_output}")
                    prompt = f"{text}\n\nVerification feedback: {verification_output}\nPlease try again."
            except Exception as e:
                logger.error(f"Error during extraction attempt {attempt}: {e}")
                if attempt == MAX_ATTEMPTS:
                    raise
        raise RuntimeError("Failed to extract and verify data after maximum attempts")
