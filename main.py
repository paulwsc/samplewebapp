# main.py - Entry point for Northflank deployment
import os
from app import app

# The application instance is created in app.py and exported as 'app'
# Northflank will automatically detect and run this

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Bind to 0.0.0.0 to accept connections from any interface
    # This ensures Northflank's health checks can reach the application
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)