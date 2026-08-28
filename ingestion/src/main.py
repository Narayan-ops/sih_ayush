"""
IP-SAKTI Sahayak Ingestion Service
Main entry point for the ingestion pipeline
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi import FastAPI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="IP-SAKTI Ingestion", version="0.1.0")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ingestion",
        "components": {
            "connectors": "initialized",
            "parsers": "initialized",
            "chunkers": "initialized",
            "embedders": "initialized",
            "transaction_manager": "initialized"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
