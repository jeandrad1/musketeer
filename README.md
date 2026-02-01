# Musketeer - 42 Campus API Tools

A collection of Python scripts to interact with the 42 school API for retrieving campus information, user data, evaluations, and logged hours.

## Overview

These scripts provide utilities to:
- Authenticate with the 42 API using OAuth2
- Fetch campus and user data
- Retrieve and process student evaluations
- Track logged hours by users
- Export data to various formats (JSON, XLSX, TXT)

## Setup

### Prerequisites
- Python 3.6+
- Virtual environment (recommended)
- 42 API credentials (UID and SECRET)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd funny
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your 42 API credentials:
```
UID=your_uid_here
SECRET=your_secret_here
```

## Scripts

### Core Authentication
- **get_token.py** - Obtains OAuth2 access token from the 42 API

### Campus & User Data
- **get_campus.py** - Retrieves campus information using paginated API calls
- **get_campus_users.py** - Fetches all users from a specific campus
- **get_users_evals.py** - Retrieves evaluations for multiple users
- **show_user.py** - Displays detailed information about a specific user

### Evaluations
- **get_evals.py** - Fetches and processes evaluations, exports to XLSX
- **get_evals_from_txt.py** - Processes evaluations from text files
- **get_user_eval.py** - Gets evaluations for a single user
- **get_pisciners_evals.py** - Specialized script for piscine (bootcamp) evaluations

### User Filtering
- **get_transcenders.py** - Retrieves users with transcender status

### Analytics
- **logged_hours.py** - Calculates and tracks logged hours by users
- **recieved_evals.py** - Analyzes evaluations received by users

## Directory Structure

```
.
├── README.md            # This file
├── .env                 # API credentials (not in git)
├── users/               # User data files
├── results/             # Output files (JSON, XLSX)
├── venv/                # Virtual environment
└── scripts              # Python scripts
```

## Usage

Most scripts require authentication via the `.env` file. Run scripts from the "scripts" directory:

```bash
python3 scripts/script_name.py
```

Some scripts read from user lists in the `users/` directory or output results to `results/`.

## Notes

- API rate limiting may apply
- Some scripts require specific user lists in `users/` directory
- Output files are typically saved in `results/` folder
- Check individual script headers for specific configuration options

## API Reference

These scripts interact with the 42 Intranet API:
- Base URL: `https://api.intra.42.fr/v2`
- Authentication: OAuth2 with client credentials flow
- Documentation: https://api.intra.42.fr/apidoc