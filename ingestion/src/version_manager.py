"""
Version Manager
Hash-based versioning with diff engine for legal amendments
Per architecture: Version-diff pipeline + human review queue
"""

from typing import List, Dict, Any, Optional
import hashlib
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class VersionManager:
    """
    Version manager for corpus with diff engine
    """
    
    def __init__(self):
        self.current_version = "1.0"
        self.version_history = {}
    
    def generate_version_hash(self, content: str) -> str:
        """
        Generate a hash for content versioning
        """
        return hashlib.sha256(content.encode()).hexdigest()
    
    def compute_diff(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """
        Compute diff between old and new content
        """
        old_hash = self.generate_version_hash(old_content)
        new_hash = self.generate_version_hash(new_content)
        
        # Simple diff detection
        if old_hash == new_hash:
            return {
                "has_changes": False,
                "old_hash": old_hash,
                "new_hash": new_hash
            }
        
        # Compute basic diff statistics
        old_lines = set(old_content.split('\n'))
        new_lines = set(new_content.split('\n'))
        
        added_lines = new_lines - old_lines
        removed_lines = old_lines - new_lines
        
        return {
            "has_changes": True,
            "old_hash": old_hash,
            "new_hash": new_hash,
            "lines_added": len(added_lines),
            "lines_removed": len(removed_lines),
            "added_sample": list(added_lines)[:5] if added_lines else [],
            "removed_sample": list(removed_lines)[:5] if removed_lines else []
        }
    
    def flag_amendments(self, diff_result: Dict[str, Any]) -> bool:
        """
        Flag content that has amendments for human review
        """
        if not diff_result["has_changes"]:
            return False
        
        # Flag for review if significant changes
        if diff_result["lines_added"] > 10 or diff_result["lines_removed"] > 10:
            logger.warning("Significant changes detected, flagging for human review")
            return True
        
        return False
    
    def create_new_version(self, current_version: str) -> str:
        """
        Create a new version number
        """
        # Simple semantic versioning
        major, minor = current_version.split('.')
        new_minor = str(int(minor) + 1)
        new_version = f"{major}.{new_minor}"
        
        self.current_version = new_version
        logger.info(f"Created new version: {new_version}")
        
        return new_version
    
    def publish_version(self, version: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Publish a version with snapshot
        """
        snapshot = {
            "version": version,
            "published_at": datetime.utcnow(),
            "chunk_count": len(chunks),
            "chunks": [chunk["metadata"]["chunk_id"] for chunk in chunks]
        }
        
        self.version_history[version] = snapshot
        logger.info(f"Published version {version} with {len(chunks)} chunks")
        
        return snapshot

# Global version manager instance
version_manager = VersionManager()
