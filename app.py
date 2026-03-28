import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
from flask import Flask, render_template, request, send_file, jsonify
import io
import base64
import webbrowser
import threading

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def detect_circle(template_path):
    img = cv2.imread(template_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours[:5]:
        area = cv2.contourArea(cnt)
        if area < 1000:
            continue
        (x, y), radius = cv2.minEnclosingCircle(cnt)
        perimeter = cv2.arcLength(cnt, True)
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        if circularity > 0.7:
            return int(x), int(y), int(radius)

    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blurred, cv2.HOUGH_GRADIENT, dp=1.2,
        minDist=min(h, w) // 2, param1=80, param2=40,
        minRadius=min(h, w) // 8, maxRadius=min(h, w) // 2
    )
    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        circles = sorted(circles, key=lambda c: c[2], reverse=True)
        cx, cy, r = circles[0]
        return int(cx), int(cy), int(r)

    return None


def merge_images(template_path, photo_bytes, cx, cy, r, zoom=1.0, offset_x=0, offset_y=0):
    template = Image.open(template_path).convert("RGBA")
    photo = Image.open(io.BytesIO(photo_bytes)).convert("RGBA")
    diameter = r * 2

    scale = max(diameter / photo.width, diameter / photo.height) * zoom
    new_w = int(photo.width * scale)
    new_h = int(photo.height * scale)
    photo = photo.resize((new_w, new_h), Image.LANCZOS)

    crop_x = (new_w - diameter) // 2 + offset_x
    crop_y = (new_h - diameter) // 2 + offset_y
    crop_x = max(0, min(crop_x, new_w - diameter))
    crop_y = max(0, min(crop_y, new_h - diameter))
    photo = photo.crop((crop_x, crop_y, crop_x + diameter, crop_y + diameter))

    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter, diameter), fill=255)

    result = template.copy()
    result.paste(photo, (cx - r, cy - r), mask)
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/detect_circle", methods=["POST"])
def detect_circle_route():
    template = request.files.get("template")
    if not template:
        return jsonify({"error": "Nenhum template enviado"}), 400
    path = os.path.join(UPLOAD_FOLDER, "template.png")
    template.save(path)
    result = detect_circle(path)
    if result:
        cx, cy, r = result
        img = cv2.imread(path)
        h, w = img.shape[:2]
        return jsonify({"cx": cx, "cy": cy, "r": r, "w": w, "h": h})
    return jsonify({"error": "Circulo nao encontrado"}), 400


@app.route("/preview", methods=["POST"])
def preview():
    data = request.json
    cx = int(data["cx"])
    cy = int(data["cy"])
    r = int(data["r"])
    zoom = float(data.get("zoom", 1.0))
    offset_x = int(data.get("offset_x", 0))
    offset_y = int(data.get("offset_y", 0))

    template_path = os.path.join(UPLOAD_FOLDER, "template.png")
    photo_path = os.path.join(UPLOAD_FOLDER, "photo.png")

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    result = merge_images(template_path, photo_bytes, cx, cy, r, zoom, offset_x, offset_y)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return jsonify({"image": b64})


@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    photo = request.files.get("photo")
    if not photo:
        return jsonify({"error": "Nenhuma foto enviada"}), 400
    path = os.path.join(UPLOAD_FOLDER, "photo.png")
    photo.save(path)
    return jsonify({"ok": True})


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    cx = int(data["cx"])
    cy = int(data["cy"])
    r = int(data["r"])
    zoom = float(data.get("zoom", 1.0))
    offset_x = int(data.get("offset_x", 0))
    offset_y = int(data.get("offset_y", 0))
    nome = data.get("nome", "participante").strip().replace(" ", "_")

    template_path = os.path.join(UPLOAD_FOLDER, "template.png")
    photo_path = os.path.join(UPLOAD_FOLDER, "photo.png")

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    result = merge_images(template_path, photo_bytes, cx, cy, r, zoom, offset_x, offset_y)
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=True, download_name=f"{nome}_drumday.png")


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.2, open_browser).start()
    app.run(debug=False, port=5000)
