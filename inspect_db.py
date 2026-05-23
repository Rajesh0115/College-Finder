import sqlite3
conn = sqlite3.connect('college_data.db')
c = conn.cursor()
c.execute("SELECT DISTINCT Status FROM cutoffs ORDER BY Status")
statuses = [r[0] for r in c.fetchall()]
for s in statuses:
    c.execute("SELECT COUNT(*) FROM cutoffs WHERE Status = ?", (s,))
    print(f"{s}: {c.fetchone()[0]} records")
conn.close()
