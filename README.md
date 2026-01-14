# Alva Session Viewer

This is a local visualization tool for viewing Alva LLM sessions and dialogs.

## Prerequisites

- Python 3.x installed
- `pip` package manager

## Quick Start

1. Open a terminal in this directory.
2. Run the start script:

   ```bash
   ./start.sh
   ```

3. Open your browser and navigate to `http://localhost:5001`.
4. Enter your Alva API Token in the interface to start browsing.

## Manual Setup

If you prefer to run it manually:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the server:
   ```bash
   python app.py
   ```

## Files

- `app.py`: Lightweight Flask server that hosts the UI and proxies API requests to avoid CORS issues.
- `index.html`: The Vue.js frontend application.
- `graphql_client.py`: Standalone CLI tool for querying data directly from the terminal.
