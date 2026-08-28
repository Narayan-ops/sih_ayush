"""
Slot Filler for Formulation Classification
LLM-driven natural language slot extraction for the decision tree
Per ADR-002: LLM only performs slot-filling, not classification judgment
"""

from typing import Dict, Any, List, Optional
import logging
import json

from ..llm.config import llm_config
from ..security.input_guard import input_guard
from ..security.prompt_template import prompt_template

logger = logging.getLogger(__name__)

class SlotFiller:
    """
    LLM-driven slot filler for the decision tree
    Extracts answers to fixed questions from natural language input
    """
    
    def __init__(self):
        self.provider = llm_config.get_provider()  # Uses self-hosted by default per ADR-001
    
    async def extract_slot(self, user_input: str, question: str, slot_name: str, options: Optional[List[str]] = None) -> Any:
        """
        Extract a specific slot value from user input using the LLM
        """
        # First sanitize the input
        sanitization_result = input_guard.sanitize_input(user_input, context="classifier")
        
        if sanitization_result.is_suspicious:
            logger.warning(f"Suspicious input detected for slot {slot_name}: {sanitization_result.flags}")
        
        # Build the prompt with clear separation
        prompt = self._build_extraction_prompt(
            sanitization_result.sanitized_input, 
            question, 
            slot_name,
            options
        )
        
        try:
            # Get LLM response
            response = await self.provider.generate(prompt)
            
            # Parse the response to extract the slot value
            slot_value = self._parse_slot_value(response.content, slot_name, options)
            
            logger.info(f"Extracted slot {slot_name} = {slot_value}")
            return slot_value
            
        except Exception as e:
            logger.error(f"Error extracting slot {slot_name}: {e}")
            return None
    
    def _build_extraction_prompt(self, user_input: str, question: str, slot_name: str, options: Optional[List[str]] = None) -> str:
        """
        Build a prompt for slot extraction
        """
        options_text = ""
        if options:
            options_text = f"\nValid options: {', '.join(options)}"
        
        prompt = f"""You are a slot extraction assistant. Your task is to extract a specific piece of information from the user's input.

USER INPUT:
{user_input}

QUESTION TO ANSWER:
{question}{options_text}

SLOT NAME: {slot_name}

Extract the answer and return it in the following JSON format:
{{"value": "extracted_value", "confidence": "high/medium/low"}}"""
        
        return prompt
    
    def _parse_slot_value(self, llm_response: str, slot_name: str, options: Optional[List[str]] = None) -> Any:
        """
        Parse the LLM response to extract the slot value
        """
        try:
            # Try to parse as JSON
            result = json.loads(llm_response)
            value = result.get("value")
            
            # Convert to appropriate type
            if options and value in options:
                return value
            elif isinstance(value, str):
                # Try to convert to boolean
                if value.lower() in ["yes", "true", "1"]:
                    return True
                elif value.lower() in ["no", "false", "0"]:
                    return False
                return value
            else:
                return value
                
        except json.JSONDecodeError:
            # Fallback: try to extract value from text
            logger.warning(f"Failed to parse JSON response for slot {slot_name}, using fallback")
            return self._extract_value_from_text(llm_response, options)
    
    def _extract_value_from_text(self, text: str, options: Optional[List[str]] = None) -> Any:
        """
        Fallback method to extract value from text
        """
        # Simple heuristic: look for yes/no first
        text_lower = text.lower()
        if "yes" in text_lower or "true" in text_lower:
            return True
        elif "no" in text_lower or "false" in text_lower:
            return False
        
        # If options provided, try to match
        if options:
            for option in options:
                if option.lower() in text_lower:
                    return option
        
        # Return the text as-is
        return text.strip()
    
    async def fill_multiple_slots(self, user_input: str, slots_to_extract: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract multiple slots from user input
        slots_to_extract: {slot_name: question}
        """
        filled_slots = {}
        
        for slot_name, question in slots_to_extract.items():
            slot_value = await self.extract_slot(user_input, question, slot_name)
            filled_slots[slot_name] = slot_value
        
        return filled_slots

# Global slot filler instance
slot_filler = SlotFiller()
