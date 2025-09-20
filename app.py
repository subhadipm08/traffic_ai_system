import os
import time
import multiprocessing as mp
import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from werkzeug.utils import secure_filename
from detection.detector import image_worker
import config
import io

def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = "uploads"

    manager = mp.Manager()
    vehicle_counts = manager.dict({"NS": 0, "SN": 0, "EW": 0, "WE": 0})
    current_green = manager.Value("s", "NS")
    processed_frames = manager.dict({"NS": None, "SN": None, "EW": None, "WE": None})
    time_remaining = manager.Value("i", 0)
    processes = {}
    
    # MODIFIED: Lane order changed to clockwise: NS -> EW -> SN -> WE
    lanes = ["NS", "EW", "SN", "WE"]

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/status")
    def status():
        return jsonify({
            "green_lane": current_green.value,
            "vehicle_counts": dict(vehicle_counts),
            "time_remaining": time_remaining.value
        })

    @app.route("/upload", methods=["POST"])
    def upload():
        for lane in ["NS", "SN", "EW", "WE"]: # Check all lanes for upload
            file_key = f"image_{lane}"
            if file_key not in request.files:
                return "Missing file for lane " + lane, 400
            
            file = request.files[file_key]
            if file.filename == "":
                return "No file selected for lane " + lane, 400

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], f"{lane}_{filename}")
            file.save(filepath)

            if lane in processes and processes[lane].is_alive():
                processes[lane].terminate()
                processes[lane].join()
            
            p = mp.Process(target=image_worker, args=(filepath, lane, vehicle_counts, processed_frames))
            p.start()
            processes[lane] = p

        return redirect(url_for("index"))

    @app.route('/processed_image/<string:lane>')
    def processed_image(lane):
        image_bytes = processed_frames.get(lane)
        if image_bytes:
            return send_file(io.BytesIO(image_bytes), mimetype='image/jpeg')
        else:
            return send_file('static/placeholder.png', mimetype='image/png')

    def signal_loop():
        lane_index = 0
        while True:
            if sum(vehicle_counts.values()) == 0 and all(f is None for f in processed_frames.values()):
                time.sleep(1)
                continue

            current_lane = lanes[lane_index]
            count = vehicle_counts[current_lane]
            
            if count == 0:
                green_time = config.EMPTY_GREEN
            else:
                green_time = min(count * config.SECONDS_PER_VEHICLE, config.MAX_GREEN)
                green_time = max(green_time, config.MIN_GREEN)
            
            current_green.value = current_lane
            print(f"[TrafficController] Green for {current_lane} → {green_time}s (vehicles={count})")
            
            start = time.time()
            while time.time() - start < green_time:
                time_remaining.value = int(green_time - (time.time() - start))
                if vehicle_counts[current_lane] == 0 and green_time > config.EMPTY_GREEN:
                    break
                time.sleep(1)
            
            time_remaining.value = 0
            lane_index = (lane_index + 1) % len(lanes)

    threading.Thread(target=signal_loop, daemon=True).start()
    return app


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    app = create_app()
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    if not os.path.exists('static/placeholder.png'):
        print("Warning: 'static/placeholder.png' not found. Please create one.")
    
    print("\n" + "="*50)
    print("🚀 Traffic AI System is running!")
    print("   Open your browser and go to -> http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, use_reloader=False)