import os
import time
import multiprocessing as mp
import threading
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response # MODIFIED: Added Response
from detection.detector import video_worker
import config


def create_app():
    app = Flask(__name__)
    app.config["UPLOAD_FOLDER"] = "uploads"

    # --- Shared state across processes ---
    manager = mp.Manager()
    vehicle_counts = manager.dict({"NS": 0, "SN": 0, "EW": 0, "WE": 0})
    current_green = manager.Value("s", "NS")
    
    # NEW: Shared dictionary to hold the latest processed frame for each lane
    processed_frames = manager.dict({"NS": None, "SN": None, "EW": None, "WE": None})

    processes = {}

    # --- Flask routes ---
    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/status")
    def status():
        return jsonify({
            "green_lane": current_green.value,
            "vehicle_counts": dict(vehicle_counts)
        })

    @app.route("/upload", methods=["POST"])
    def upload():
        lane = request.form.get("lane")
        if "video" not in request.files or lane not in vehicle_counts:
            return "Invalid upload", 400

        file = request.files["video"]
        if file.filename == "":
            return "No file selected", 400

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], f"{lane}.mp4")
        file.save(filepath)

        if lane in processes and processes[lane].is_alive():
            processes[lane].terminate()
            processes[lane].join()
        
        # MODIFIED: Pass the processed_frames dictionary to the worker
        p = mp.Process(target=video_worker, args=(filepath, lane, vehicle_counts, processed_frames))
        p.start()
        processes[lane] = p

        return redirect(url_for("index"))

    # NEW: Route to stream video feed for a specific lane
    @app.route('/video_feed/<string:lane>')
    def video_feed(lane):
        def generate_frames(target_lane):
            while True:
                time.sleep(0.1) # Yield CPU
                frame_bytes = processed_frames.get(target_lane)
                if frame_bytes:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

        return Response(generate_frames(lane), mimetype='multipart/x-mixed-replace; boundary=frame')


    # --- Background traffic controller ---
    def signal_loop():
        # (This function remains unchanged)
        lanes = ["NS", "SN", "EW", "WE"]
        lane_index = 0
        while True:
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
                if vehicle_counts[current_lane] == 0:
                    break
                time.sleep(1)
            lane_index = (lane_index + 1) % len(lanes)

    threading.Thread(target=signal_loop, daemon=True).start()
    return app


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    app = create_app()
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    print("\n" + "="*50)
    print("🚀 Traffic AI System is running!")
    print("   Open your browser and go to -> http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, use_reloader=False)