import rumps
import sqlite3
import sys, os
from datetime import datetime, timedelta
from pathlib import Path
import webbrowser
import tempfile

# === DB konumu ===
APP_NAME = "focustimes"
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

DB_FILE = str(APP_SUPPORT_DIR / "focustimes.db")

def resource_path(relative_path):
    """PyInstaller ile bundle içindeki dosya yolunu çöz."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

ICON_PATH = resource_path("focustimes.icns")

class FocusTimesApp(rumps.App):
    def __init__(self):
        super(FocusTimesApp, self).__init__(
            "focustimes",
            icon=ICON_PATH,
            menu=["Start", "Finish", None, "Statistics"],  # Quit zaten otomatik ekleniyor
        )

        self.start_time = None
        self.end_time = None
        self.duration = None

        self._init_db()

    # === DB init ===
    def _init_db(self):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time TEXT,
                end_time TEXT,
                duration INTEGER,
                tag TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    # === Timer ===
    @rumps.clicked("Start")
    def start_timer(self, _):
        if self.start_time:
            rumps.alert("Already running!")
            return
        self.start_time = datetime.now()
        rumps.notification(
            "focustimes", "Started", f"Start: {self.start_time.strftime('%H:%M:%S')}"
        )

    @rumps.clicked("Finish")
    def finish_timer(self, _):
        if not self.start_time:
            rumps.alert("Not running!")
            return

        self.end_time = datetime.now()
        self.duration = int((self.end_time - self.start_time).total_seconds())

        # Etiket sor
        tag_input = rumps.Window(
            "Enter tag for this session:",
            "Save Session",
            default_text="focus-time",
        ).run()

        tag = tag_input.text if tag_input.clicked else "focus-time"

        # DB'ye kaydet
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sessions (start_time, end_time, duration, tag) VALUES (?, ?, ?, ?)",
            (
                self.start_time.isoformat(),
                self.end_time.isoformat(),
                self.duration,
                tag,
            ),
        )
        conn.commit()
        conn.close()

        rumps.notification(
            "focustimes",
            "Session Saved",
            f"Duration: {timedelta(seconds=self.duration)}\nTag: {tag}",
        )

        self.start_time = None
        self.end_time = None
        self.duration = None

    # === Statistics (HTML) ===
    @rumps.clicked("Statistics")
    def show_statistics(self, _):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        now = datetime.now()

        def get_total(start):
            cur.execute(
                "SELECT SUM(duration) FROM sessions WHERE start_time >= ?",
                (start.isoformat(),),
            )
            result = cur.fetchone()[0]
            return result or 0

        today_start = datetime(now.year, now.month, now.day)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = datetime(now.year, now.month, 1)
        year_start = datetime(now.year, 1, 1)

        totals = {
            "Today": get_total(today_start),
            "This Week": get_total(week_start),
            "This Month": get_total(month_start),
            "This Year": get_total(year_start),
        }

        # Son 10 kayıt
        cur.execute(
            "SELECT start_time, end_time, duration, tag FROM sessions ORDER BY start_time DESC LIMIT 10"
        )
        last_sessions = cur.fetchall()

        # Tag bazlı (son 50 etiket)
        cur.execute(
            """
            SELECT tag,
                SUM(CASE WHEN start_time >= ? THEN duration ELSE 0 END) as today,
                SUM(CASE WHEN start_time >= ? THEN duration ELSE 0 END) as week,
                SUM(CASE WHEN start_time >= ? THEN duration ELSE 0 END) as month,
                SUM(CASE WHEN start_time >= ? THEN duration ELSE 0 END) as year
            FROM sessions
            GROUP BY tag
            ORDER BY COUNT(*) DESC
            LIMIT 50
            """,
            (
                today_start.isoformat(),
                week_start.isoformat(),
                month_start.isoformat(),
                year_start.isoformat(),
            ),
        )
        tag_stats = cur.fetchall()
        conn.close()

        # === HTML üret ===
        html = """
        <html>
        <head>
            <title>focustimes Statistics</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h2 { margin-top: 30px; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
                th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <h1>focustimes - Statistics</h1>
            <h2>Last 10 Sessions</h2>
            <table>
                <tr><th>Start</th><th>End</th><th>Duration</th><th>Tag</th></tr>
        """
        for start_time, end_time, duration, tag in last_sessions:
            start_str = datetime.fromisoformat(start_time).strftime("%Y-%m-%d %H:%M:%S")
            end_str = datetime.fromisoformat(end_time).strftime("%Y-%m-%d %H:%M:%S")
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            duration_str = f"{hours}h {minutes}m"
            html += f"<tr><td>{start_str}</td><td>{end_str}</td><td>{duration_str}</td><td>{tag}</td></tr>"
        html += "</table>"

        html += """
            <h2>Total Durations</h2>
            <table>
                <tr><th>Period</th><th>Duration</th></tr>
        """
        for label, seconds in totals.items():
            html += f"<tr><td>{label}</td><td>{seconds//3600}h {(seconds%3600)//60}m</td></tr>"
        html += "</table>"

        html += """
            <h2>Tag Stats (Top 50)</h2>
            <table>
                <tr><th>Tag</th><th>Today</th><th>This Week</th><th>This Month</th><th>This Year</th></tr>
        """
        for tag, t_day, t_week, t_month, t_year in tag_stats:
            html += f"<tr><td>{tag}</td>"
            html += f"<td>{t_day//3600}h {(t_day%3600)//60}m</td>"
            html += f"<td>{t_week//3600}h {(t_week%3600)//60}m</td>"
            html += f"<td>{t_month//3600}h {(t_month%3600)//60}m</td>"
            html += f"<td>{t_year//3600}h {(t_year%3600)//60}m</td></tr>"
        html += "</table></body></html>"

        # Geçici dosya oluştur ve tarayıcıda aç
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as f:
            f.write(html)
            temp_path = f.name

        webbrowser.open(f"file://{temp_path}")


if __name__ == "__main__":
    FocusTimesApp().run()