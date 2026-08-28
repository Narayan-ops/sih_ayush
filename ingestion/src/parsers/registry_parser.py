"""
Registry Parser
Parses structured registry data (patents, trademarks, GI, etc.)
"""

from typing import List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class RegistryParser:
    """
    Parser for structured registry data
    """
    
    def __init__(self):
        pass
    
    def parse(self, raw_data: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse structured registry data
        """
        try:
            # Try to parse as JSON
            data = json.loads(raw_data)
            
            # Convert to chunks if it's a list
            if isinstance(data, list):
                chunks = []
                for i, item in enumerate(data):
                    chunk = {
                        "content": json.dumps(item),
                        "metadata": {
                            **metadata,
                            "registry_type": metadata.get("registry_type", "unknown"),
                            "item_index": i
                        }
                    }
                    chunks.append(chunk)
                return chunks
            else:
                # Single item
                return [{
                    "content": raw_data,
                    "metadata": metadata
                }]
                
        except json.JSONDecodeError:
            # Not JSON, treat as plain text
            return [{
                "content": raw_data,
                "metadata": metadata
            }]

# Global parser instance
registry_parser = RegistryParser()
