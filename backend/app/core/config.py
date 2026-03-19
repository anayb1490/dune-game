"""
Application configuration.

This is where we keep all the settings our server needs in one place.
If you ever need to change a port, add a new frontend URL, or tweak
a game rule, you change it here instead of hunting through 20 files.
"""

# ---------------------------------------------------------------------------
# CORS (Cross-Origin Resource Sharing)
# ---------------------------------------------------------------------------
#
# Here's the problem CORS solves:
#
# Your React frontend runs at  http://localhost:5173  (Vite's default)
# Your FastAPI backend runs at http://localhost:8000
#
# These are different "origins" (different port = different origin).
# Browsers have a security rule: JavaScript on one origin can NOT make
# requests to a different origin unless the server explicitly says
# "yes, I trust that origin."
#
# Without CORS config, your React app's fetch() calls to the API would
# be silently blocked by the browser with an error like:
#   "Access to fetch at 'http://localhost:8000' from origin
#    'http://localhost:5173' has been blocked by CORS policy"
#
# So we whitelist our frontend origins below. When the browser asks
# "is localhost:5173 allowed?", our server responds "yes."

ALLOWED_ORIGINS: list[str] = [
    "*"
]


# ---------------------------------------------------------------------------
# Server defaults
# ---------------------------------------------------------------------------

API_PREFIX: str = "/api"
APP_TITLE: str = "Dune Board Game API"
APP_VERSION: str = "0.1.0"
