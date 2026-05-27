"""
Flask API for ibiza.db DuckDB tables
Run: python app.py
Endpoints:
  GET /tables          → list all tables
  GET /table/<name>    → full table data as JSON
  GET /table/<name>?limit=50  → paginated
"""

import duckdb
from flask import Flask, jsonify, request
from flask_cors import CORS

DB_PATH = "database/ibiza.db"

app = Flask(__name__)
CORS(app)  # Required so your GitHub Pages HTML can call this API

def get_con():
    return duckdb.connect(DB_PATH, read_only=True)


@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "endpoints": ["/tables", "/table/<name>"]
    })


@app.route("/tables")
def list_tables():
    con = get_con()
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    con.close()
    return jsonify({"tables": tables})


@app.route("/table/<string:table_name>")
def get_table(table_name):
    limit = request.args.get("limit", default=None, type=int)
    offset = request.args.get("offset", default=0, type=int)

    con = get_con()

    # Safety: verify table exists
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    if table_name not in tables:
        con.close()
        return jsonify({"error": f"Table '{table_name}' not found"}), 404

    # Total row count
    total = con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]

    # Build query
    query = f'SELECT * FROM "{table_name}"'
    if limit:
        query += f" LIMIT {limit} OFFSET {offset}"

    # Use fetchall() + description to guarantee column order
    result = con.execute(query)
    columns = [desc[0] for desc in result.description]
    raw_rows = result.fetchall()
    con.close()

    # Serialize rows as ordered lists (not dicts) to prevent misalignment
    def serialize(val):
        if val is None:
            return None
        # Handle non-JSON-serializable types (date, Decimal, etc.)
        if hasattr(val, 'isoformat'):
            return val.isoformat()
        try:
            return float(val) if isinstance(val, __import__('decimal').Decimal) else val
        except Exception:
            return str(val)

    rows = [[serialize(v) for v in row] for row in raw_rows]

    return jsonify({
        "table": table_name,
        "total_rows": total,
        "returned_rows": len(rows),
        "offset": offset,
        "columns": columns,
        "rows": rows,          # list of lists, order guaranteed
    })


if __name__ == "__main__":
    print(f"Connecting to {DB_PATH}...")
    # Quick validation on startup
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
        con.close()
        print(f"✓ Found tables: {tables}")
    except Exception as e:
        print(f"✗ Could not open {DB_PATH}: {e}")

    app.run(debug=True, port=5000)
