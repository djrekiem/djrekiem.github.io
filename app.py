"""
Flask API for ibiza.db DuckDB tables
Run: python app.py
"""

import duckdb
import decimal
from flask import Flask, jsonify, request
from flask_cors import CORS

DB_PATH = "database/ibiza.db"

app = Flask(__name__)
CORS(app, origins="*", supports_credentials=False)

@app.after_request
def add_headers(response):
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.route("/", methods=["GET", "OPTIONS"])
def index():
    return jsonify({"status": "ok", "endpoints": ["/tables", "/table/<name>"]})

@app.route("/tables", methods=["GET", "OPTIONS"])
def list_tables():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    con = duckdb.connect(DB_PATH, read_only=True)
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    con.close()
    return jsonify({"tables": tables})

@app.route("/table/<string:table_name>", methods=["GET", "OPTIONS"])
def get_table(table_name):
    if request.method == "OPTIONS":
        return jsonify({}), 200

    limit  = request.args.get("limit",  default=None, type=int)
    offset = request.args.get("offset", default=0,    type=int)

    con = duckdb.connect(DB_PATH, read_only=True)
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    if table_name not in tables:
        con.close()
        return jsonify({"error": f"Table '{table_name}' not found"}), 404

    total = con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    query = f'SELECT * FROM "{table_name}"'
    if limit:
        query += f" LIMIT {limit} OFFSET {offset}"

    result   = con.execute(query)
    columns  = [desc[0] for desc in result.description]
    raw_rows = result.fetchall()
    con.close()

    def serialize(val):
        if val is None:
            return None
        if hasattr(val, 'isoformat'):
            return val.isoformat()
        if isinstance(val, decimal.Decimal):
            return float(val)
        return val

    rows = [[serialize(v) for v in row] for row in raw_rows]

    return jsonify({
        "table":         table_name,
        "total_rows":    total,
        "returned_rows": len(rows),
        "offset":        offset,
        "columns":       columns,
        "rows":          rows,
    })

if __name__ == "__main__":
    print(f"Connecting to {DB_PATH}...")
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        con.close()
        print(f"✓ Found tables: {tables}")
    except Exception as e:
        print(f"✗ Could not open {DB_PATH}: {e}")

    app.run(debug=True, port=5000)
