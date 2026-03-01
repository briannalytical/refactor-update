# Refactor Job Application Tracker

## Features

- Log completed job applications & create a recruiter address book
- Thoroughly track and update your progress through the application pipeline
- Creates scheduled tasks to remind user of next action steps for application follow-up

## Prerequsites
```bash
# Clone the repository
git clone https://github.com/briannalytical/refactor-update.git

# Navigate to project directory
cd your-repo-name

# Install dependencies
pip install -r requirements.txt

# Install Python interpreter (if needed)
pip install python3
```

## Configuration
This app was developed using postgreSQL and it is highly encouraged that you use postgreSQL-friendly software. pgAdmin is recommended.
1. Download pgAdmin4
  ~ https://www.pgadmin.org/
  ~ Click "Servers" > Register and name refactor-update
  ~ Under "Connections" verify default settings: localhost (5432) and "postgres" for maintenance database
2. Open refactor-update server and there will be a pop-up confirming connection to server

## Usage
This app is best run in a terminal or can be run in an IDE. If using IDE, verify that Python3 interpreter has been installed. PyCharm is recommended.
```bash
# Navigate to your installation directory and run:
python script.py
```
