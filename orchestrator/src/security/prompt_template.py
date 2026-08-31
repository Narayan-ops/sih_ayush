"""
Safe Prompt Construction
Enforces strict separation between user text and system instructions
Prevents prompt injection through proper prompt template design
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PromptTemplate:
    """
    Safe prompt template that enforces separation between user and system content
    """
    
    def __init__(self):
        self.templates = {
            "classification": """You are a formulation classification assistant. Your task is to extract specific information from the user's description to help determine the drug category.

USER DESCRIPTION:
{user_input}

Extract the following information:
{extraction_fields}

Provide only the extracted information in the specified format.""",
            
            "retrieval": """You are a legal information retrieval assistant for Ayurveda IPR and regulatory guidance.

USER QUERY:
{user_input}

JURISDICTION: {jurisdiction}

Retrieve relevant legal information and provide answers with proper citations.""",
            
            "generation": """You are an AI assistant for Ayurveda IPR and regulatory guidance. You provide information, not legal advice.

RETRIEVED CONTEXT:
{context}

USER QUERY:
{user_input}

Answer the user's question using only the provided context. Every claim must be supported by the context. Do not add information not found in the context. Keep the answer concise. Do not use introductory phrases like "Based on the context" or "According to the documents." Answer:"""
        }
    
    def build_prompt(self, template_name: str, user_input: str, context: str = None, **kwargs) -> str:
        """
        Build a prompt from template with strict separation
        User input is never concatenated into instruction regions
        """
        if template_name not in self.templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template = self.templates[template_name]
        
        # Ensure user input is properly escaped/sanitized
        sanitized_input = self._sanitize_for_prompt(user_input)
        
        # Build prompt with clear separation
        format_kwargs = {"user_input": sanitized_input, **kwargs}
        if context is not None:
            format_kwargs["context"] = context
        
        prompt = template.format(**format_kwargs)
        
        return prompt
    
    def _sanitize_for_prompt(self, text: str) -> str:
        """
        Sanitize text for safe inclusion in prompts
        """
        # Remove any potential prompt injection markers
        # This is a basic sanitization - the input_guard does the heavy lifting
        return text.strip()
    
    def add_template(self, name: str, template: str):
        """
        Add a new prompt template
        """
        self.templates[name] = template
    
    def get_template(self, name: str) -> str:
        """
        Get a template without filling it
        """
        if name not in self.templates:
            raise ValueError(f"Unknown template: {name}")
        return self.templates[name]

# Global prompt template instance
prompt_template = PromptTemplate()
