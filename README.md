# Refactor Job Application Tracker

## Features

- Log all completed job applications
- Schedules daily tasks to prompt user persistence and reminders in the follow-up process
- View all applications and update your path through the application pipeline with application status updates
- Creates a contact address book of recruiters, hiring managers etc. to follow up with for future opportunities
- Schedule interview dates and times
- Add notes about the company, role, interview prep
- Automatically updates application status to the next step upon completed task.

## Prerequsites
```bash
# Clone the repository
git clone https://github.com/briannalytical/refactor-update.git

# Open that directory
cd refactor-update

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration
This app connects to a PostgreSQL database using a 'DATABASE_URL' environment variable inside the '.env' file in the root directory.

The required string format is:
```text
postgresql://[USERNAME]:[PASSWORD]@[HOST]:[PORT]/[DATABASE_NAME]
```
If there is a valid server connection but no database exists with the passed `DATABASE_NAME` value the string this will attempt to create a database for you with that name.

Create a local `.env` file in the project root directory (copy `.env.example`) and fill in your specific `DATABASE_URL`. 

**Example (Local pgAdmin):**
```text
DATABASE_URL=postgresql://postgres:secretpassword@localhost:5432/refactor_db
```

**Example (Cloud Neon Console):**
```text
DATABASE_URL=postgresql://neondb_owner:pass123@ep-cool-pool-123.us-east-2.aws.neon.tech/neon_db?sslmode=require&channel_binding=require
```

## Use
This app is best run in a terminal or can be run in an IDE. If using IDE, verify that Python3 interpreter has been installed. PyCharm is recommended and the community edition is free.
```bash
# Navigate to your installation directory and run:
python3 script.py
```
