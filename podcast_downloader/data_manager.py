import sqlite3

DB_NAME = "podcasts.db"

def db_init():
    """Creates the podcasts table if it doesn't exist."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS podcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                feed_url TEXT NOT NULL,
                download_dir TEXT NOT NULL,
                username TEXT,
                password TEXT
            )
        """)
        conn.commit()

def db_get_podcasts():
    """Fetches all saved podcasts (ID and Name) for the dropdown."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM podcasts ORDER BY name")
        return cursor.fetchall()

def db_get_podcast_details(podcast_id):
    """Fetches the details of a specific podcast by ID."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM podcasts WHERE id = ?", (podcast_id,))
        return cursor.fetchone()

def db_save_podcast(name, url, dir, user, pwd):
    """Saves or updates a podcast in the database. Uses the NAME as a unique key."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO podcasts (name, feed_url, download_dir, username, password)
            VALUES (?, ?, ?, ?, ?)
        """, (name, url, dir, user, pwd))
        conn.commit()

def db_delete_podcast(podcast_id):
    """Deletes a podcast from the database by ID."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM podcasts WHERE id = ?", (podcast_id,))
        conn.commit()