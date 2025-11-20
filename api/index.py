from flask import Flask, request, jsonify
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Fetch variables
CONNECTION_STRING = os.getenv("COIN_STRING")
app = Flask(__name__, static_folder="static")

def get_connection():
    return psycopg2.connect(CONNECTION_STRING)


# ---------------------------
#  RUTAS BÁSICAS
# ---------------------------

@app.route('/')
def home():
    return 'API IoT funcionando'


@app.route('/about')
def about():
    return 'About'


# ---------------------------
#  INSERTAR VALORES (Raspberry, ESP32)
# ---------------------------

@app.route("/sensor/<int:sensor_id>", methods=["POST"])
def insert_sensor_value(sensor_id):
    value = request.args.get("value", type=float)
    if value is None:
        return jsonify({"error":"Missing 'value' query parameter"}), 400

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO sensores (sensor_id, value) VALUES (%s, %s)", (sensor_id, value))
        conn.commit()

        return jsonify({
            "message":"Value inserted",
            "sensor_id": sensor_id,
            "value": value
        }), 201

    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


# ---------------------------
#  API REST PARA EL DASHBOARD
# ---------------------------

# Obtener lista de IDs
@app.route("/api/devices")
def api_devices():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT sensor_id FROM sensores ORDER BY sensor_id;")
        ids = [row[0] for row in cur.fetchall()]
        return jsonify(ids)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


# Obtener datos recientes de todos los sensores
@app.route("/api/devices/data")
def api_devices_data():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (sensor_id)
                sensor_id, value, unit, created_at
            FROM sensores
            ORDER BY sensor_id, created_at DESC;
        """)

        devices = []
        for row in cur.fetchall():
            devices.append({
                "id": row[0],
                "value": row[1],
                "unit": row[2] if row[2] else "",
                "timestamp": row[3].strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(devices)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


# Datos en vivo de 1 dispositivo
@app.route("/api/devices/<int:sensor_id>")
def api_device(sensor_id):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT value, unit, created_at
            FROM sensores
            WHERE sensor_id = %s
            ORDER BY created_at DESC
            LIMIT 1;
        """, (sensor_id,))

        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Sensor not found"}), 404

        return jsonify({
            "id": sensor_id,
            "name": f"Sensor {sensor_id}",
            "value": row[0],
            "unit": row[1] if row[1] else "",
            "timestamp": row[2].strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


# Historial de un sensor
@app.route("/api/devices/<int:sensor_id>/history")
def api_device_history(sensor_id):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT value, created_at
            FROM sentidos
            WHERE sensor_id = %s
            ORDER BY created_at DESC
            LIMIT 50;
        """, (sensor_id,))

        rows = cur.fetchall()

        history = [
            {
                "value": r[0],
                "timestamp": r[1].strftime('%Y-%m-%d %H:%M:%S')
            } for r in rows
        ]

        return jsonify(history)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


# ---------------------------
#  SERVIR DASHBOARD (HTML ESTÁTICO)
# ---------------------------

@app.route("/dashboard")
def dashboard():
    return app.send_static_file("index.html")


# ---------------------------
#  RUN
# ---------------------------

if __name__ == "__main__":
    app.run(debug=True)
