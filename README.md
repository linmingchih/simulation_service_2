# Simulation Service Example

This repository contains a minimal implementation of the architecture described in `AGENTS.md`.
It provides a Flask web application with a simple flow that demonstrates the basic structure
of a simulation service.

## Quick Start

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python run.py
   ```
3. Navigate to `http://localhost:5000` to see the available flows.

## Project Structure

- `app/` - Application package
  - `routes.py` - Basic routes for deck and flow steps
  - `flows/` - Pluggable flow modules
  - `templates/` - Jinja2 templates
- `jobs/` - Folder where job data is stored
- `run.py` - Application entry point

This is a simplified example intended for demonstration purposes.
