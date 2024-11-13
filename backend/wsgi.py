
# This file contains the WSGI configuration required to serve up your
# web application at http://dkfpv.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler

import sys
import os

# Add your project directory to the sys.path
project_home = '/home/dkfpv/pdf_converter'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Import your FastAPI app
from main import app
from fastapi.middleware.wsgi import WSGIMiddleware

# Create WSGI app
application = WSGIMiddleware(app)
