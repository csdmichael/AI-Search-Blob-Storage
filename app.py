"""
App Service entry point.
Azure App Service Python looks for app.py or application.py in wwwroot by default.
This file re-exports the FastAPI app from api/server.py.
"""
import os
import sys

# Ensure the project root (where this file lives) is on sys.path
# so that `import config` and `from api.server import app` both work
# regardless of the working directory chosen by the App Service runtime.
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from api.server import app  # noqa: F401, E402
