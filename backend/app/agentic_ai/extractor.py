import os
import json
import asyncio
import logging
import re
from io import BytesIO
from dotenv import load_dotenv
import requests
from PIL import Image as PILImage
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage
from autogen_core import Image

load_dotenv()

MAX_IMAGES = 3
LLM_TIMEOUT = 30
MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)

ex_prompt = os.getenv("extract_prompt")
vr_prompt = os.getenv("verify_prompt")

class ExtractorAgent:
    def __init__(self, llm_client):
        self.llm = AssistantAgent(
            name="Extractor",
            description="Will extract data from user input",
            system_message=ex_prompt,
            model_client=llm_client
        )
        self.verifier = AssistantAgent(
            name="Verifier",
            description="Will Verify data from Extractor input",
            system_message=vr_prompt,
            model_client=llm_client
        )

    async def _call_llm_with_timeout(self, payload):
        """
        Handles both images and text using MultiModalMessage.
        """
        try:
            logger.debug(f"Calling LLM with payload: {payload}")

            content_parts = []

            # Prioritize URL check over file extension check
            if isinstance(payload, str) and payload.startswith("http"):
                try:
                    response = requests.get(payload)
                    if response.status_code == 200:
                        pil_image = PILImage.open(BytesIO(response.content))
                        content_parts.append(Image(pil_image))
                    else:
                        logger.error(f"Failed to fetch image from URL: {payload} with status code {response.status_code}")
                        raise Exception(f"Failed to fetch image from URL: {payload} with status code {response.status_code}")
                except requests.RequestException as e:
                    logger.error(f"RequestException while fetching image from URL: {payload}: {e}")
                    raise
            elif isinstance(payload, str) and payload.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                pil_image = PILImage.open(payload)
                content_parts.append(Image(pil_image))
            elif isinstance(payload, PILImage.Image):
                content_parts.append(Image(payload))
            else:
                content_parts.append(str(payload))

            message = MultiModalMessage(content=content_parts, source="user")

            result = await asyncio.wait_for(
                self.llm.run(task=message),
                timeout=LLM_TIMEOUT
            )

            logger.debug(f"LLM returned: {result}")
            if hasattr(result, "messages"):
                content = result.messages[-1].content
                if isinstance(content, list):
                    content = "\n".join(str(part) for part in content)
                else:
                    content = str(content)
                return content
            else:
                return str(result)

        except asyncio.TimeoutError:
            logger.error("LLM call timed out")
            raise
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def extract_image(self, image, user_text=None):
        """
        Extracts from images and optional user_text, merging structured data.
        """
        if image is None and not user_text:
            logger.warning("No image or user_text provided to extract_image")
            return

        images = []
        if image is not None:
            images = image if isinstance(image, list) else [image]
            if not (1 <= len(images) <= MAX_IMAGES):
                raise ValueError(f"Number of images must be between 1 and {MAX_IMAGES}, got {len(images)}")
            logger.info(f"Extracting from {len(images)} image(s)")
        else:
            logger.info("No images provided, only user_text will be used")

        unstructured_text = ""
        merged_data = {
            "problem": {
                "title": None,
                "statement": "",
                "constraint": [],
                "test_case": []
            }
        }

        if images:
            try:
                tasks = [self._call_llm_with_timeout(img) for img in images]
                image_texts = await asyncio.gather(*tasks)
                
                for text_blob in image_texts:
                    try:
                        match = re.search(r'```json\s*(\{.*?\})\s*```', text_blob, re.DOTALL)
                        json_str = match.group(1) if match else text_blob
                        
                        start = json_str.find('{')
                        end = json_str.rfind('}')
                        if start != -1 and end != -1:
                            json_str = json_str[start:end+1]
                        
                        data = json.loads(json_str)
                        problem = data.get("problem", {})

                        if not merged_data["problem"]["statement"] and problem.get("statement"):
                            merged_data["problem"]["statement"] = problem["statement"]
                        
                        if problem.get("constraint"):
                            for c in problem["constraint"]:
                                if c not in merged_data["problem"]["constraint"]:
                                    merged_data["problem"]["constraint"].append(c)

                        if problem.get("test_case"):
                             for tc in problem["test_case"]:
                                if tc not in merged_data["problem"]["test_case"]:
                                    merged_data["problem"]["test_case"].append(tc)
                    except (json.JSONDecodeError, AttributeError):
                        unstructured_text += f"\n---\n{text_blob}"

            except Exception as e:
                logger.error(f"Error during image extraction: {e}")
                raise

        # Combine the merged structured data with any unstructured text
        final_prompt_text = json.dumps(merged_data, indent=4) + unstructured_text
        if user_text:
            final_prompt_text += f"\n\n--- Additional Context ---\n{user_text}"

        source_input = {
            "source_images": images if images else None,
            "source_text": user_text if user_text else None
        }

        await self.extract_text(final_prompt_text, source_input=source_input)

    async def extract_text(self, text, source_input=None):
        """
        Extracts structured info from text/images and verifies it.
        """
        prompt = text
        verification_input = {
            "source_images": None,
            "source_text": None
        }

        if source_input:
            verification_input["source_images"] = source_input.get("source_images", None)
            verification_input["source_text"] = source_input.get("source_text", None)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            logger.info(f"Extraction attempt {attempt}")
            try:
                extracted = await self._call_llm_with_timeout(prompt)

                if isinstance(extracted, dict):
                    extracted_json = extracted
                elif isinstance(extracted, str):
                    try:
                        # Find json block within the text
                        match = re.search(r'```json\s*(\{.*?\})\s*```', extracted, re.DOTALL)
                        if match:
                            json_str = match.group(1)
                        else: # Fallback to finding first { and last }
                            start = extracted.find('{')
                            end = extracted.rfind('}')
                            if start != -1 and end != -1:
                                json_str = extracted[start:end+1]
                            else:
                                json_str = extracted
                        extracted_json = json.loads(json_str)

                    except json.JSONDecodeError:
                        convert_prompt = f"Please convert the following text to valid JSON:\n{extracted}"
                        extracted_json_str = await self._call_llm_with_timeout(convert_prompt)
                        try:
                            extracted_json = json.loads(extracted_json_str)
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse JSON after conversion attempt")
                            extracted_json = None
                else:
                    extracted_json = None

                verifier_payload = {
                    "extracted": extracted_json if extracted_json is not None else extracted,
                    "source_images": verification_input["source_images"],
                    "source_text": verification_input["source_text"]
                }

                verification_result = await asyncio.wait_for(
                    self.verifier.run(task=json.dumps(verifier_payload)),
                    timeout=LLM_TIMEOUT
                )
                if hasattr(verification_result, "messages"):
                    verification_output = verification_result.messages[-1].content
                    if isinstance(verification_output, list):
                        verification_output = "\n".join(str(part) for part in verification_output)
                    else:
                        verification_output = str(verification_output)
                else:
                    verification_output = str(verification_result)

                logger.debug(f"Verifier output: {verification_output}")

                verified = False
                try:
                    verifier_json = json.loads(verification_output)
                    if isinstance(verifier_json, dict):
                        verified = verifier_json.get("verified", False) is True
                except json.JSONDecodeError:
                    lowered_output = str(verification_output).strip().lower()
                    if any(keyword in lowered_output for keyword in ['yes', 'true', 'correct', 'valid', 'verified']):
                        verified = True

                if verified:
                    logger.info("Saving extracted data to data.json now")
                    to_save = None
                    if extracted_json is not None:
                        to_save = extracted_json
                    else:
                        to_save = {"raw_output": extracted}
                    with open("data.json", "w") as f:
                        json.dump(to_save, f)
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

