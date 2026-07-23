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
# Make new directory for application
mkdir refactor-update

# Open that directory
cd refactor update

# Clone the repository
git clone https://github.com/briannalytical/refactor-update.git

# Install dependencies
pip install -r requirements.txt

# Install Python interpreter (if needed)
pip install python3

# Set up Python environment & imports
python3 -m venv .venv
source .venv/bin/activate
pip install psycopg2-binary

```

## Configuration
This app was developed using postgreSQL and it is highly encouraged that you use postgreSQL-friendly software. pgAdmin is recommended.
1. Download pgAdmin4
  ~ https://www.pgadmin.org/
  ~ Click "Servers" > Register and name refactor-update
  ~ Under "Connections" verify default settings: localhost (5432) and "postgres" for maintenance database
2. Open refactor-update server and there will be a pop-up confirming connection to server
3. Note: as this is a machine-locked program, if the server is not running, the program will not run and you will be prompted to restart the server in order to proceed

## Use
This app is best run in a terminal or can be run in an IDE. If using IDE, verify that Python3 interpreter has been installed. PyCharm is recommended and the community edition is free.
```bash
# Navigate to your installation directory and run:
python3 script.py
```
