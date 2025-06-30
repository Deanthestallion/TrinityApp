
from flask import Flask, request, jsonify, send_file
import os
import uuid
import threading
import subprocess
import cv2

app = Flask(__name__)
OUTPUT_DIR = "outputs"
THUMBNAIL_DIR = "thumbnails"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(THUMBNAIL_DIR, exist_ok=True)

def run_auto_editor(input_path, output_path):
    try:
        print(f"[INFO] Starting auto-editor for {input_path}")
        subprocess.run([
            'auto-editor', input_path,
            '--output_file', output_path,
            '--no-open'
        ], check=True)
        print(f"[INFO] Finished processing {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] auto-editor failed: {e}")

def extract_video_thumbnail(input_path, output_path, start=0, duration=5):
    try:
        subprocess.run([
            'ffmpeg',
            '-ss', str(start),
            '-i', input_path,
            '-t', str(duration),
            '-c', 'copy',
            output_path
        ], check=True)
        print(f"[INFO] Video thumbnail created at {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] FFmpeg failed: {e}")

@app.route("/process", methods=["POST"])
def process_video():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No video uploaded"}), 400

    uid = uuid.uuid4().hex
    input_path = os.path.join(OUTPUT_DIR, f"input_{uid}.mp4")
    output_path = os.path.join(OUTPUT_DIR, f"output_{uid}.mp4")
    image_thumb_path = os.path.join(THUMBNAIL_DIR, f"thumb_{uid}.jpg")
    video_thumb_path = os.path.join(THUMBNAIL_DIR, f"thumbclip_{uid}.mp4")

    file.save(input_path)
    print(f"[INFO] File saved to {input_path}")

    # Extract image thumbnail
    cap = cv2.VideoCapture(input_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(image_thumb_path, frame)
        print(f"[INFO] Image thumbnail saved to {image_thumb_path}")
    cap.release()

    # Extract video thumbnail
    extract_video_thumbnail(input_path, video_thumb_path, start=5, duration=6)

    # Start auto-editor in background
    threading.Thread(target=run_auto_editor, args=(input_path, output_path)).start()

    return jsonify({
        "message": "Processing started",
        "video_download_url": f"/download/{os.path.basename(output_path)}",
        "thumbnail_image_url": f"/thumbnail/{os.path.basename(image_thumb_path)}",
        "thumbnail_video_url": f"/thumbnail/{os.path.basename(video_thumb_path)}"
    })

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "File not ready or not found"}), 404
    return send_file(path, as_attachment=True)

@app.route("/thumbnail/<filename>", methods=["GET"])
def serve_thumbnail(filename):
    path = os.path.join(THUMBNAIL_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Thumbnail not found"}), 404
    mimetype = "video/mp4" if filename.endswith(".mp4") else "image/jpeg"
    return send_file(path, mimetype=mimetype)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "Video processor with image + video thumbnail is running"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
