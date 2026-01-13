# Python Web Application with Handsontable and DuckDB

This is a FastAPI web application that integrates Handsontable (Excel-like spreadsheet) with a DuckDB database for CRUD operations.

## Features

- Excel-like interface using Handsontable
- Full CRUD operations (Create, Read, Update, Delete)
- Data persistence with DuckDB
- User authentication and registration
- Responsive web interface

## Deployment to Northflank

This application is configured for deployment to Northflank using the following files:
- `Dockerfile` - Defines the container image
- `northflank.yml` - Northflank service configuration
- `requirements.txt` - Python dependencies

### Environment Variables
- `PORT` - Port number assigned by Northflank (automatically set)
- `DB_PATH` - Path to the database file (defaults to `./database.db` for persistence)

### Deployment Steps

1. Fork this repository to your GitHub account
2. Create a new Service on Northflank
3. Connect to your forked repository
4. Northflank will automatically detect this is a Docker environment
5. The application will be deployed using the Dockerfile and northflank.yml configuration

## Local Development

### Prerequisites

- Python 3.7+
- pip (Python package installer)

### Installation

1. Clone or download this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

1. Start the development server:

```bash
uvicorn main:app --reload
```

2. Open your browser and navigate to `http://localhost:8000`

## Usage

- Register a new account or use the default admin account (admin/admin123)
- View the sample data in the Handsontable grid
- Edit cells directly in the grid
- Click "Add Row" to add new records
- Select rows and click "Delete Selected" to remove records
- Click "Save Changes" to persist all changes to the database

## Project Structure

- `app.py`: Main FastAPI application with all routes and database operations
- `main.py`: Entry point for production deployment
- `requirements.txt`: Python dependencies
- `Dockerfile`: Container configuration for deployment
- `northflank.yml`: Northflank deployment configuration
- `templates/index.html`: HTML template with Handsontable integration
- `static/script.js`: Client-side JavaScript code
- `static/style.css`: Styling for the application
- `.gitignore`: Git ignore file for deployment

## Technologies Used

- FastAPI: Modern, fast web framework for building APIs with Python
- DuckDB: Embeddable analytical database that connects directly to Python
- Handsontable: JavaScript/HTML5 spreadsheet component
- Pandas: Data manipulation and analysis library
- Uvicorn: ASGI server for running FastAPI applications
- Passlib: Password hashing library

## Notes for Production

- The application uses in-memory session storage which will reset on restarts
- For production use, consider implementing persistent session storage
- The default admin account (admin/admin123) should be changed after first login
- Database persistence is handled via the DB_PATH environment variable on Northflank