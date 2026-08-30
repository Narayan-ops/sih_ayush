"""
Statute Parser
Parses legal statutes into section/article-level chunks
Per architecture: Structural segmentation, not fixed-window chunking
"""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class StatuteParser:
    """
    Parser for legal statutes
    Performs structural segmentation (section/article-level)
    """
    
    def __init__(self):
        # Patterns for detecting sections and articles
        self.section_pattern = re.compile(r'\bSection\s+\d+[A-Z]?\b', re.IGNORECASE)
        self.article_pattern = re.compile(r'\bArticle\s+\d+[A-Z]?\b', re.IGNORECASE)
        # Pattern for both numeric (1), (2) and lettered (a), (b) clauses
        self.clause_pattern = re.compile(r'\b\([a-z0-9]+\)\b', re.IGNORECASE)
    
    def parse(self, raw_text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse raw statute text into structured chunks
        """
        chunks = []
        
        # Split by sections
        sections = self.section_pattern.split(raw_text)
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            # Extract section number if available
            section_match = self.section_pattern.search(section)
            section_num = section_match.group() if section_match else f"section_{i}"
            
            # Further split by clauses if needed
            clauses = self._split_by_clauses(section)
            
            for j, clause in enumerate(clauses):
                if not clause.strip():
                    continue
                
                chunk = {
                    "content": clause.strip(),
                    "section": section_num,
                    "clause": f"clause_{j}" if len(clauses) > 1 else None,
                    "metadata": {
                        **metadata,
                        "chunk_type": "section",
                        "chunk_index": i
                    }
                }
                chunks.append(chunk)
        
        logger.info(f"Parsed {len(chunks)} chunks from statute")
        return chunks
    
    def parse_json(self, structured_data: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse already structured JSON data into chunks
        Use this when data is already correctly chunked, sourced, with clause IDs
        """
        chunks = []
        
        for i, item in enumerate(structured_data):
            chunk = {
                "content": item.get("content", item.get("text", "")),
                "section": item.get("section", "unknown"),
                "clause": item.get("clause", item.get("clause_id")),
                "source_id": item.get("source_id", f"source_{i}"),
                "metadata": {
                    **metadata,
                    "chunk_type": "structured",
                    "chunk_index": i,
                    **item.get("metadata", {})
                }
            }
            chunks.append(chunk)
        
        logger.info(f"Parsed {len(chunks)} chunks from structured JSON")
        return chunks
    
    def _split_by_clauses(self, text: str) -> List[str]:
        """
        Split text by clauses if they exist
        """
        # Simple clause splitting by numbered parentheses
        # This can be enhanced for more complex legal text
        clauses = self.clause_pattern.split(text)
        
        # Reconstruct clauses with their numbers
        reconstructed = []
        for i, clause in enumerate(clauses):
            if i == 0:
                reconstructed.append(clause)
            else:
                reconstructed.append(f"({i}) {clause}")
        
        return reconstructed
    
    def extract_metadata(self, raw_text: str) -> Dict[str, Any]:
        """
        Extract metadata from statute text
        """
        metadata = {
            "title": self._extract_title(raw_text),
            "act_number": self._extract_act_number(raw_text),
            "year": self._extract_year(raw_text),
            "enforcement_date": self._extract_enforcement_date(raw_text)
        }
        return metadata
    
    def _extract_title(self, text: str) -> str:
        """Extract act title from text"""
        # Simple heuristic: first non-empty line
        lines = text.split('\n')
        for line in lines:
            if line.strip():
                return line.strip()
        return "Unknown Title"
    
    def _extract_act_number(self, text: str) -> str:
        """Extract act number from text"""
        # Pattern: "Act No. X of YYYY"
        match = re.search(r'Act\s+No\.\s*(\d+)', text, re.IGNORECASE)
        return match.group(1) if match else "Unknown"
    
    def _extract_year(self, text: str) -> str:
        """Extract year from text"""
        match = re.search(r'\b(19|20)\d{2}\b', text)
        return match.group() if match else "Unknown"
    
    def _extract_enforcement_date(self, text: str) -> str:
        """Extract enforcement date from text"""
        # Pattern: "commenced on [date]"
        match = re.search(r'commenced\s+on\s+([^\n]+)', text, re.IGNORECASE)
        return match.group(1).strip() if match else "Unknown"

# Global parser instance
statute_parser = StatuteParser()
