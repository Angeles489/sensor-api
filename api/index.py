from flask import Flask, request, jsonify, render_template
import psycopg2
import os

CONNECTION_STRING = os.getenv("COIN_STRING")
app = Flask(__name__)

def get_connection():
    return psycopg2.connect(CONNECTION_STRING)

@app.route("/")
def dispositivos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM dispositivos ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return render_template("dashboard.html", dispositivos=rows)

@app.route("/sensor/<int:sensor_id>", methods=["POST"])
def insert_sensor_value(sensor_id):
    value = request.args.get("value", type=float)
    if value is None:
        return jsonify({"error": "Missing 'value' query parameter"}), 400
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sensores (sensor_id, value) VALUES (%s, %s)",
            (sensor_id, value)
        )
        conn.commit()
        return jsonify({
            "message": "Sensor value inserted successfully",
            "sensor_id": sensor_id,
            "value": value
        }), 201
    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if "conn" in locals():
            conn.close()

@app.route("/api/dashboard/<sensor_id>")
def api_dashboard(sensor_id):
    conn = get_connection()
    cur = conn.cursor()

    if sensor_id == "all":
        cur.execute("""
            SELECT d.nombre, s.sensor_id, s.value, s.created_at
            FROM sensores s
            JOIN dispositivos d ON s.sensor_id = d.id
            ORDER BY s.created_at DESC
            LIMIT 100;
        """)
        rows = cur.fetchall()

        sensores = {}
        for name, sid, val, ts in rows:
            sensores.setdefault(sid, []).append((ts, val))

        datasets = []
        for sid, items in sensores.items():
            items = sorted(items)
            datasets.append({
                "label": f"Sensor {sid}",
                "data": [v for (_, v) in items],
                "tension": 0.3,
                "borderWidth": 2,
                "fill": False
            })

        timestamps = sorted({ts for group in sensores.values() for (ts, _) in group})
        timestamps = [t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps]

        conn.close()
        return jsonify({
            "rows": [
                {
                    "sensor_name": name,
                    "sensor_id": sid,
                    "value": val,
                    "created_at": ts.strftime('%Y-%m-%d %H:%M:%S')
                }
                for name, sid, val, ts in rows
            ],
            "timestamps": timestamps,
            "datasets": datasets
        })

    cur.execute("""
    SELECT d.nombre, s.value, s.created_at
    FROM sensores s
    JOIN dispositivos d ON s.sensor_id = d.id
    WHERE sensor_id = %s
    ORDER BY s.created_at DESC
    LIMIT 10;
    """, (sensor_id,))
    rows = cur.fetchall()
    conn.close()

    values = [r[1] for r in rows][::-1]
    timestamps = [r[2].strftime('%Y-%m-%d %H:%M:%S') for r in rows][::-1]

    return jsonify({
        "rows": [
            {
                "sensor_id": sensor_id,
                "sensor_name": r[0],
                "value": r[1],
                "created_at": r[2].strftime('%Y-%m-%d %H:%M:%S')
            }
            for r in rows
        ],
        "timestamps": timestamps,
        "datasets": [{
            "label": f"Sensor {sensor_id}",
            "data": values,
            "borderWidth": 2,
            "tension": 0.3,
            "fill": True
        }]
    })

