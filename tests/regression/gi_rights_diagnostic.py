"""
GI Rights Query Diagnostic Script
Shows detailed retrieval information for the GI rights query
"""

import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_gi_rights_query():
    """Test GI rights query and show detailed retrieval info"""
    
    query = "What are the rights for a registered geographical indication?"
    
    # First, let's directly query the GI domain to see what chunks are available
    logger.info("=" * 80)
    logger.info("DIAGNOSTIC: GI Rights Query")
    logger.info("=" * 80)
    logger.info(f"Query: {query}")
    logger.info("")
    
    # Test with the API
    try:
        response = requests.post(
            "http://localhost:8001/query",
            json={
                "query": query,
                "jurisdiction": "in"
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        logger.info("API Response:")
        logger.info(f"Answer: {result.get('answer', 'N/A')[:200]}...")
        logger.info(f"Confidence: {result.get('confidence_score', 0.0):.2f}")
        logger.info(f"Citations: {len(result.get('citations', []))}")
        
        logger.info("\nCitation Details:")
        for i, citation in enumerate(result.get('citations', [])[:5]):
            logger.info(f"  Citation {i+1}:")
            logger.info(f"    Section: {citation.get('section', 'N/A')}")
            logger.info(f"    Article: {citation.get('article', 'N/A')}")
            logger.info(f"    Confidence: {citation.get('confidence', 0.0):.3f}")
        
        # Check if the answer mentions 21(1)(b)
        answer_text = result.get('answer', '')
        if '21(1)(b)' in answer_text or 'exclusive right' in answer_text.lower():
            logger.info("\n✓ Answer contains rights information (21(1)(b) or 'exclusive right')")
        else:
            logger.info("\n✗ Answer does NOT contain rights information (21(1)(b) or 'exclusive right')")
            logger.info("This suggests clause 21(1)(b) is not being retrieved effectively")
        
    except Exception as e:
        logger.error(f"API request failed: {e}")
        logger.info("Make sure the orchestrator is running on http://localhost:8001")

if __name__ == "__main__":
    test_gi_rights_query()
