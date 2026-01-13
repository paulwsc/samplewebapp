import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import duckdb
import logging
import secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Use environment variable for database path, default to local file
    db_path = os.getenv('DB_PATH', 'sample.db')
    conn = duckdb.connect(db_path, config={'allow_unsigned_extensions': True})

    # Create employees table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            age INTEGER,
            email VARCHAR,
            department VARCHAR
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
        sample = [
            (1, "Paul Smith",     32, "paul@example.com",     "Engineering"),
            (2, "Lisa Wong",      28, "lisa@example.com",      "Design"),
            (3, "Tom Chen",       45, "tom@example.com",       "Management"),
            (4, "Anna Lee",       29, "anna@example.com",      "Marketing"),
            (5, "David Kim",      38, "david@example.com",     "Sales")
        ]
        conn.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", sample)
        conn.commit()
        print("Sample data inserted")

    # Create sequence for user IDs
    conn.execute("CREATE SEQUENCE IF NOT EXISTS user_id_seq START 1;")

    # Create users table using the sequence for the default value
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY DEFAULT nextval('user_id_seq'),
            username VARCHAR UNIQUE NOT NULL,
            email VARCHAR UNIQUE NOT NULL,
            hashed_password VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Check if admin user exists, if not create one
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        # Create default admin user
        admin_username = "admin"
        admin_email = "admin@example.com"
        admin_password = "admin123"  # Change this in production

        hashed_password = pwd_context.hash(admin_password)
        conn.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
            [admin_username, admin_email, hashed_password]
        )
        conn.commit()
        print(f"Default admin user created: {admin_username}")

    # Store connection in global variable or use dependency injection
    app.state.conn = conn

    yield  # This is where the application runs

    # Shutdown cleanup
    conn.close()

app = FastAPI(title="Handsontable with DuckDB", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/data")
async def get_data(request: Request):
    try:
        conn = request.app.state.conn
        result = conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
        columns = [desc[0] for desc in conn.description]

        data = []
        for row in result:
            record = {}
            for i, col in enumerate(columns):
                value = row[i]
                if hasattr(value, 'item'):
                    record[col] = value.item()
                else:
                    record[col] = value
            data.append(record)

        return data
    except Exception as e:
        logger.error(f"Error in /data endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data")
async def add_data(request: Request):
    try:
        item = await request.json()
        conn = request.app.state.conn
        name = item.get('name', '').strip()
        age = item.get('age')
        email = item.get('email', '').strip()
        department = item.get('department', '').strip()

        if not name and not email and age is None and not department:
            raise HTTPException(status_code=400, detail="Cannot add completely empty record")

        # Always generate new ID
        next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM employees").fetchone()[0]

        conn.execute(
            "INSERT INTO employees (id, name, age, email, department) VALUES (?, ?, ?, ?, ?)",
            [next_id, name, age, email, department]
        )
        conn.commit()

        return {"message": "Record added", "id": next_id}
    except Exception as e:
        logger.error(f"Error in /data POST endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/data/{id}")
async def update(id: int, request: Request):
    try:
        item = await request.json()
        conn = request.app.state.conn

        values = [
            item.get('name', '').strip(),
            item.get('age'),
            item.get('email', '').strip(),
            item.get('department', '').strip(),
            id
        ]

        result = conn.execute("""
            UPDATE employees
            SET name = ?, age = ?, email = ?, department = ?
            WHERE id = ?
        """, values)

        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")

        return {"message": "Updated successfully"}
    except Exception as e:
        logger.error(f"Error in /data PUT endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/data/{id}")
async def delete(id: int, request: Request):
    try:
        conn = request.app.state.conn
        result = conn.execute("DELETE FROM employees WHERE id = ?", [id])
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Record not found")

        return {"message": "Deleted successfully"}
    except Exception as e:
        logger.error(f"Error in /data DELETE endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Authentication helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_username(conn, username: str):
    result = conn.execute("SELECT * FROM users WHERE username = ?", [username]).fetchone()
    if result:
        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
            "hashed_password": result[3],
            "created_at": result[4]
        }
    return None


def authenticate_user(conn, username: str, password: str):
    user = get_user_by_username(conn, username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user


# Session management (for simplicity, using in-memory storage)
active_sessions = {}


def create_session(user_id: int) -> str:
    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=24)  # 24 hour session
    }
    return session_token


def get_current_user_from_session(session_token: str):
    if session_token in active_sessions:
        session_data = active_sessions[session_token]
        if session_data["expires_at"] > datetime.now():
            return session_data["user_id"]
        else:
            # Session expired, remove it
            del active_sessions[session_token]
    return None


def logout_session(session_token: str):
    if session_token in active_sessions:
        del active_sessions[session_token]


# User registration endpoint
@app.post("/register")
async def register_user(request: Request):
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="Username, email, and password are required")

        conn = request.app.state.conn

        # Check if user already exists
        existing_user = get_user_by_username(conn, username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        # Check if email already exists
        existing_email = conn.execute("SELECT * FROM users WHERE email = ?", [email]).fetchone()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash the password
        hashed_password = get_password_hash(password)

        # Insert new user
        conn.execute(
            "INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)",
            [username, email, hashed_password]
        )
        conn.commit()

        # Get the auto-generated ID
        new_user_id = conn.execute("SELECT id FROM users WHERE username = ?", [username]).fetchone()[0]

        return {"message": "User registered successfully", "user_id": new_user_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /register endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# User login endpoint
@app.post("/login")
async def login_user(request: Request):
    try:
        data = await request.json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            raise HTTPException(status_code=400, detail="Username and password are required")

        conn = request.app.state.conn

        user = authenticate_user(conn, username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Create session
        session_token = create_session(user["id"])

        return {
            "message": "Login successful",
            "session_token": session_token,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /login endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# User logout endpoint
@app.post("/logout")
async def logout_user(request: Request):
    try:
        data = await request.json()
        session_token = data.get('session_token', '').strip()

        if not session_token:
            raise HTTPException(status_code=400, detail="Session token is required")

        logout_session(session_token)

        return {"message": "Logout successful"}
    except Exception as e:
        logger.error(f"Error in /logout endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Get current user info endpoint
@app.get("/user/me")
async def get_current_user(request: Request):
    try:
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not session_token:
            raise HTTPException(status_code=401, detail="Session token is required")

        user_id = get_current_user_from_session(session_token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired session")

        conn = request.app.state.conn
        user = conn.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", [user_id]).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "created_at": user[3]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /user/me endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# For Render deployment, we don't include the if __name__ == "__main__" block
# Render will handle starting the application