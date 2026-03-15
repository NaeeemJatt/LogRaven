# LogRaven — FastAPI Application Entry Point
#
# PURPOSE:
#   Creates and configures the FastAPI application.
#   Registers all API routers with their URL prefixes.
#   Mounts local file storage at /files for development PDF serving.
#   Startup event: validates license before any other initialization.
#   Configures CORS, exception handlers, and middleware.
#
# CRITICAL: validate_license() must be called FIRST in startup event.
#           If license is invalid, SystemExit is raised and app does not start.
#
# TODO Month 1 Week 1: Implement this file.

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="LogRaven API",
    description="Watch your logs. Find the threat.",
    version="1.0.0",
)

# TODO: Add CORS middleware
# TODO: Add global exception handlers
# TODO: Mount StaticFiles at /files for local/reports/
# TODO: Add startup event that calls validate_license()
# TODO: Register all routers from api/router.py
