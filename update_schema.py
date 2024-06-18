import sqlite3

# Connect to the existing SQLite database or create a new one
conn = sqlite3.connect('airdrop.db')
c = conn.cursor()

# Create the users table with the necessary columns if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    wallet TEXT,
    balance INTEGER DEFAULT 0,
    last_claim TIMESTAMP,
    last_withdraw TIMESTAMP,
    invites INTEGER DEFAULT 0
)
''')

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database schema ensured.")