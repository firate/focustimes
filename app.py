import rumps
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "focustimes.db"  # dikkat: çoğul


def format_duration(seconds: int) -> str:
    """Convert seconds into 'Xh Ym' format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return "0m"


def init_db():
    """DB yoksa tabloları oluştur."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        start_time TEXT,
        end_time TEXT,
        duration_seconds INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS session_tags (
        session_id INTEGER,
        tag_id INTEGER,
        PRIMARY KEY(session_id, tag_id),
        FOREIGN KEY(session_id) REFERENCES sessions(id),
        FOREIGN KEY(tag_id) REFERENCES tags(id)
    )
    """)

    conn.commit()
    conn.close()


class WorkTimerApp(rumps.App):
    def __init__(self):
        super(WorkTimerApp, self).__init__(
            "WorkTimer",
            icon=None,
            menu=["Start", "Finish", None, "Statistics"],
        )

        self.start_time = None
        self.end_time = None
        self.duration = None



     

    # -------------------------
    # MENU ACTIONS
    # -------------------------
    @rumps.clicked("Start")
    def start_timer(self, _):
        if self.start_time is not None and self.end_time is None:
            rumps.alert("Already running!")
            return
        self.start_time = datetime.now()
        self.end_time = None
        self.duration = None
        rumps.notification(
            "WorkTimer", "Started", f"Start: {self.start_time.strftime('%H:%M:%S')}"
        )

    @rumps.clicked("Finish")
    def finish_session(self, _):
        if not self.start_time:
            rumps.alert("Not running!")
            return

        self.end_time = datetime.now()
        self.duration = int((self.end_time - self.start_time).total_seconds())

        tag_input = rumps.Window(
            "Enter tags (comma separated):",
            "Finish Session",
            default_text="focus-time",
        ).run()

        if tag_input.clicked:
            try:
                session_name = self.start_time.strftime("%Y-%m-%d %H:%M")

                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()

                # insert session
                c.execute(
                    "INSERT INTO sessions (name, start_time, end_time, duration_seconds) VALUES (?, ?, ?, ?)",
                    (
                        session_name,
                        self.start_time.isoformat(),
                        self.end_time.isoformat(),
                        self.duration,
                    ),
                )
                session_id = c.lastrowid

                # insert tags
                tags = [t.strip() for t in tag_input.text.split(",") if t.strip()]
                for tag in tags:
                    c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    c.execute("SELECT id FROM tags WHERE name=?", (tag,))
                    tag_id = c.fetchone()[0]
                    c.execute(
                        "INSERT OR IGNORE INTO session_tags (session_id, tag_id) VALUES (?, ?)",
                        (session_id, tag_id),
                    )

                conn.commit()
                conn.close()

                rumps.notification(
                    "WorkTimer", "Saved", f"Session saved with tags: {', '.join(tags)}"
                )
            except sqlite3.Error as e:
                rumps.alert(f"DB Error: {e}")

        # reset state
        self.start_time = None
        self.end_time = None
        self.duration = None

    @rumps.clicked("Statistics")
    def show_statistics(self, _):
        try:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()

            now = datetime.now()
            start_of_today = datetime(now.year, now.month, now.day)
            start_of_week = start_of_today - timedelta(days=now.weekday())
            start_of_month = datetime(now.year, now.month, 1)
            start_of_year = datetime(now.year, 1, 1)

            def total_since(start):
                c.execute(
                    "SELECT SUM(duration_seconds) FROM sessions WHERE start_time >= ?",
                    (start.isoformat(),),
                )
                result = c.fetchone()[0]
                return int(result or 0)

            # --- Tablo 1: Genel süreler
            daily = total_since(start_of_today)
            weekly = total_since(start_of_week)
            monthly = total_since(start_of_month)
            yearly = total_since(start_of_year)

            stats_text = []
            stats_text.append("=== TOTAL DURATIONS ===")
            stats_text.append(f"Today   : {format_duration(daily)}")
            stats_text.append(f"This Week: {format_duration(weekly)}")
            stats_text.append(f"This Month: {format_duration(monthly)}")
            stats_text.append(f"This Year : {format_duration(yearly)}\n")

            # --- Tablo 2: Etiket bazında, son 10 popüler etiket
            stats_text.append("=== TOP 10 TAGS ===")

            c.execute("""
                SELECT t.name, COUNT(*) as usage_count
                FROM tags t
                JOIN session_tags st ON t.id = st.tag_id
                GROUP BY t.name
                ORDER BY usage_count DESC
                LIMIT 10
            """)
            top_tags = [row[0] for row in c.fetchall()]

            for tag in top_tags:
                stats_text.append(f"\n[{tag}]")
                def total_for_tag(start):
                    c.execute(
                        """
                        SELECT SUM(s.duration_seconds)
                        FROM sessions s
                        JOIN session_tags st ON s.id = st.session_id
                        JOIN tags t ON t.id = st.tag_id
                        WHERE t.name = ? AND s.start_time >= ?
                        """,
                        (tag, start.isoformat()),
                    )
                    result = c.fetchone()[0]
                    return int(result or 0)

                stats_text.append(f"  Today     : {format_duration(total_for_tag(start_of_today))}")
                stats_text.append(f"  This Week : {format_duration(total_for_tag(start_of_week))}")
                stats_text.append(f"  This Month: {format_duration(total_for_tag(start_of_month))}")
                stats_text.append(f"  This Year : {format_duration(total_for_tag(start_of_year))}")

            conn.close()

            # Pencere göster
            rumps.Window(
                "\n".join(stats_text),
                title="Statistics",
                ok=None,
                cancel="Close",
            ).run()

        except sqlite3.Error as e:
            rumps.alert(f"DB Error: {e}")

if __name__ == "__main__":
    init_db()
    WorkTimerApp().run()