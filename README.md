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
   # waitress is included in requirements for serving the app
   ```
2. Run the application:
   ```bash
   python run.py
   ```
3. Navigate to `http://localhost:5000` to see the available flows.

User accounts are stored in `users.json` and loaded on startup, so any users
added through the admin interface will persist across restarts.

Each user can also edit personal settings such as AEDT/EDB versions, language,
and color scheme from the *Settings* page after logging in. These preferences
are saved in `users.json` for future sessions.

## Project Structure

- `app/` - Application package
  - `routes.py` - Basic routes for deck and flow steps
  - `flows/` - Pluggable flow modules
  - `templates/` - Jinja2 templates
- `jobs/` - Folder where job data is stored
- `users.json` - Stored user accounts
- `run.py` - Application entry point

This is a simplified example intended for demonstration purposes.

## Step 1 Input Handling

The `Flow_SIwave_SYZ` example now accepts a single design file for the first
step. Upload either a `.brd` file or a zipped `.aedb` archive. The uploaded file
is processed and saved as `design.aedb` in the job's output directory.

All subsequent steps reference `output/design.aedb`, ensuring a consistent path
regardless of the original input type.
