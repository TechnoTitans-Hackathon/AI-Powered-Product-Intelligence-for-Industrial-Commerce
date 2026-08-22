import sqlite3
conn = sqlite3.connect('server/data/freeapi.db')
c = conn.cursor()
c.execute("SELECT platform, model_id FROM models WHERE model_id LIKE '%gpt-oss%' OR model_id LIKE '%120b%';")
for row in c.fetchall():
    print(row)
