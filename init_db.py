import duckdb
conn = duckdb.connect('sample.db', config={'allow_unsigned_extensions': True})

# Create users table
conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username VARCHAR UNIQUE NOT NULL,
        email VARCHAR UNIQUE NOT NULL,
        hashed_password VARCHAR NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Check if admin user exists, if not create one
if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
    # Create default admin user
    from passlib.context import CryptContext
    # Use a different scheme that doesn't rely on bcrypt if there are issues
    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    admin_username = "admin"
    admin_email = "admin@example.com"
    admin_password = "admin123"  # Change this in production

    hashed_password = pwd_context.hash(admin_password)
    # Get the next ID
    next_id_result = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM users").fetchone()
    next_id = next_id_result[0]
    conn.execute(
        "INSERT INTO users (id, username, email, hashed_password) VALUES (?, ?, ?, ?)",
        [next_id, admin_username, admin_email, hashed_password]
    )
    conn.commit()
    print(f"Default admin user created: {admin_username}")
else:
    print("Admin user already exists")

# Verify users table
result = conn.execute("SELECT * FROM users").fetchall()
print("Users table contains:")
for row in result:
    print(f"ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")

conn.close()