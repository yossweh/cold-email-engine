"""WSGI entry point for production deployment."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.dashboard.app import app

if __name__ == '__main__':
    app.run()
