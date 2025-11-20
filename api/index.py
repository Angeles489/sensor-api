from flask import Flask,request, jsonify, render_template
import psycopg2
from dotenv import load_dotenv
import os


# Fetch variables
CONNECTION_STRING=os.getenv("COIN_STRING")
app = Flask(__name__)

def get_connection():
    return psycopg2.connect(CONNECTION_STRING)
    
@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/about')
def about():
    return 'About'


@app.route('/sensor')
def sensor():
    # ConnecT to the database
    try:
        connection = get_connection()
        print("Connection successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("SELECT* FROM sensores;")
        result = cursor.fetchall()
        print("Current Time:", result)
    
        # Close the cursor and connection
        cursor.close()
        connection.close()
        return f"Current Time {result}."
    
    except Exception as e:
        return f"Failed to connect: {e}"

@app.route("/sensor/<int:sensor_id>",methods=["POST"])
def insert_sensor_value(sensor_id):
    value=request.args.get("value",type=float)
    if value is None:
        return jsonify({"error":"Missing 'value' query parameter"}),400
    try:
        conn=get_connection()
        cur=conn.cursor()
        cur.execute("INSERT INTO sensores (sensor_id, value) VALUES (%s, %s)",(sensor_id,value))
        conn.commit()
        return jsonify({"message":"Sensor value inserted successfully","sensor_id":sensor_id,"value":value}),201
    except psycopg2.Error as e:
        return jsonify({"error":str(e)}),500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route("/hello")
def hello():
    return render_template("hello.html")
    
@app.route("/sensor/<int:sensor_id>")
def get_sensor(sensor_id):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get the latest 10 values
        cur.execute("""
            SELECT value, created_at
            FROM sensores
            WHERE sensor_id = %s
            ORDER BY created_at DESC
            LIMIT 10;
        """, (sensor_id,))
        rows = cur.fetchall()

        # Convert to lists for graph
        values = [r[0] for r in rows][::-1]        # reverse for chronological order
        timestamps = [r[1].strftime('%Y-%m-%d %H:%M:%S') for r in rows][::-1]
        
        return render_template("sensor.html", sensor_id=sensor_id, values=values, timestamps=timestamps, rows=rows)

    except Exception as e:
        return f"<h3>Error: {e}</h3>"

    finally:
        if 'conn' in locals():
            conn.close()
                       

@app.route("/dispositivos")
def dispositivos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nombre FROM dispositivos ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return render_template("dispositivos.html", dispositivos=rows)

@app.route("/vista/<device_id>")
def vista_dispositivo(device_id):
    conn = get_connection()
    cur = conn.cursor()

    if device_id == "all":
        cur.execute("""
            SELECT sensor_id, value, created_at
            FROM sensores
            ORDER BY created_at DESC
            LIMIT 50;
        """)
        rows = cur.fetchall()
        conn.close()
        return render_template("todos.html", rows=rows)

    # solo un dispositivo
    cur.execute("""
        SELECT value, created_at
        FROM sensores
        WHERE sensor_id = %s
        ORDER BY created_at DESC
        LIMIT 10;
    """, (device_id,))
    rows = cur.fetchall()
    conn.close()

    values = [r[0] for r in rows][::-1]
    timestamps = [r[1].strftime('%Y-%m-%d %H:%M:%S') for r in rows][::-1]

    return render_template("sensor.html",
                           sensor_id=device_id,
                           values=values,
                           timestamps=timestamps,
                           rows=rows)

@app.route("/api/sensor/<int:sensor_id>")
def api_sensor(sensor_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT value, created_at
        FROM sensores
        WHERE sensor_id = %s
        ORDER BY created_at DESC
        LIMIT 10;
    """, (sensor_id,))

    rows = cur.fetchall()
    conn.close()

    return jsonify({
        "values": [r[0] for r in rows][::-1],
        "timestamps": [r[1].strftime('%Y-%m-%d %H:%M:%S') for r in rows][::-1],
        "rows": [{"value": r[0], "created_at": r[1].strftime('%Y-%m-%d %H:%M:%S')} for r in rows]
    })
