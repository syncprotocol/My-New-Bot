import sqlite3

# Connect to the existing SQLite database
conn = sqlite3.connect('airdrop.db')
c = conn.cursor()

# Check and add missing columns if necessary
try:
    c.execute('ALTER TABLE users ADD COLUMN balance INTEGER DEFAULT 0')
except sqlite3.OperationalError:
    print("Column 'balance' already exists.")

try:
    c.execute('ALTER TABLE users ADD COLUMN last_claim TIMESTAMP')
except sqlite3.OperationalError:
    print("Column 'last_claim' already exists.")

try:
    c.execute('ALTER TABLE users ADD COLUMN last_withdraw TIMESTAMP')
except sqlite3.OperationalError:
    print("Column 'last_withdraw' already exists.")

try:
    c.execute('ALTER TABLE users ADD COLUMN invites INTEGER DEFAULT 0')
except sqlite3.OperationalError:
    print("Column 'invites' already exists.")

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database schema updated with missing columns.")