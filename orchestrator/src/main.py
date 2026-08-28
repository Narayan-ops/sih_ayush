"""
IP-SAKTI Sahayak Orchestrator Service
Main entry point for the orchestrator service
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IP-SAKTI Orchestrator", version="0.1.0")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "orchestrator",
        "components": {
            "llm_provider": "initialized",
            "classifier": "initialized",
            "retrieval": "pending",
            "citation": "pending"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
