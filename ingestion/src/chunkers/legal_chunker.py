"""
Legal Chunker
Performs structural segmentation of legal text
Per architecture: Not fixed-window chunking, preserves citation granularity
"""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

class LegalChunker:
    """
    Legal text chunker with structural segmentation
    Preserves citation granularity (section/article/clause level)
    """
    
    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size
        
        # Legal text patterns
        self.section_pattern = re.compile(r'\bSection\s+\d+[A-Z]?\b', re.IGNORECASE)
        self.article_pattern = re.compile(r'\bArticle\s+\d+[A-Z]?\b', re.IGNORECASE)
        self.subsection_pattern = re.compile(r'\b\([a-z]\d*\)\b')
        self.proviso_pattern = re.compile(r'\bProvided\s+that\b', re.IGNORECASE)
    
    def chunk(self, parsed_sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Further chunk parsed sections while preserving legal structure
        """
        chunks = []
        
        for section in parsed_sections:
            content = section["content"]
            section_num = section.get("section", "unknown")
            
            # Check if section needs further chunking
            if len(content) > self.max_chunk_size:
                # Split by subsections or paragraphs
                sub_chunks = self._split_large_section(content, section_num)
                chunks.extend(sub_chunks)
            else:
                # Keep as is
                chunks.append(section)
        
        logger.info(f"Created {len(chunks)} chunks from {len(parsed_sections)} sections")
        return chunks
    
    def _split_large_section(self, content: str, section_num: str) -> List[Dict[str, Any]]:
        """
        Split a large section while preserving legal structure
        """
        chunks = []
        
        # Try to split by subsections first
        subsections = self.subsection_pattern.split(content)
        
        if len(subsections) > 1:
            # Reconstruct subsections with their markers
            for i, subsection in enumerate(subsections):
                if i == 0:
                    full_text = subsection
                else:
                    # Find the subsection marker
                    match = self.subsection_pattern.search(content)
                    if match:
                        marker = match.group()
                        full_text = f"{marker} {subsection}"
                    else:
                        full_text = subsection
                
                if len(full_text) > self.max_chunk_size:
                    # Further split by paragraphs
                    para_chunks = self._split_by_paragraphs(full_text, section_num)
                    chunks.extend(para_chunks)
                else:
                    chunks.append({
                        "content": full_text.strip(),
                        "section": section_num,
                        "subsection": f"subsection_{i}" if i > 0 else None,
                        "chunk_type": "subsection"
                    })
        else:
            # Split by paragraphs
            para_chunks = self._split_by_paragraphs(content, section_num)
            chunks.extend(para_chunks)
        
        return chunks
    
    def _split_by_paragraphs(self, text: str, section_num: str) -> List[Dict[str, Any]]:
        """
        Split text by paragraphs while respecting sentence boundaries
        """
        paragraphs = text.split('\n\n')
        chunks = []
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed size limit
            if len(current_chunk) + len(para) > self.max_chunk_size and current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "section": section_num,
                    "chunk_index": chunk_index,
                    "chunk_type": "paragraph"
                })
                current_chunk = para
                chunk_index += 1
            else:
                current_chunk += "\n\n" + para if current_chunk else para
        
        # Add remaining content
        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "section": section_num,
                "chunk_index": chunk_index,
                "chunk_type": "paragraph"
            })
        
        return chunks
    
    def add_citation_metadata(self, chunks: List[Dict[str, Any]], metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Add citation metadata to chunks
        Ensures each chunk has source_id, section, version_hash per architecture
        """
        enhanced_chunks = []
        
        for i, chunk in enumerate(chunks):
            enhanced_chunk = {
                **chunk,
                "metadata": {
                    **chunk.get("metadata", {}),
                    **metadata,
                    "chunk_id": f"{metadata.get('source_id', 'unknown')}_{i}",
                    "version_hash": metadata.get("version_hash", "1.0"),
                    "jurisdiction": metadata.get("jurisdiction", "india"),
                    "domain": metadata.get("domain", "statutes")
                }
            }
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks

# Global chunker instance
legal_chunker = LegalChunker()
