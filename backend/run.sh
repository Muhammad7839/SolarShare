#!/bin/bash
# Development launcher for the SolarShare backend API and hosted web app.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
