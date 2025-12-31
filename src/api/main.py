"""
FastAPI Main Entry Point

Entry point for uvicorn server.
"""

from src.api.app import create_app

# Create app instance for uvicorn
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
