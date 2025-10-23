# app.py (예시)
import os
from flask import Flask, request, send_from_directory, render_template

app = Flask(__name__, static_folder='static', template_folder='templates')

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# 업로드 처리 예시 (이미 있으면 기존 로직 유지)
@app.post("/upload")
def upload():
    f = request.files.get("photo")
    if not f:
        return "no file", 400
    # HEIC → JPEG 변환 예시 (필요할 때만)
    if f.filename.lower().endswith(".heic"):
        from PIL import Image
        import pillow_heif
        heif = pillow_heif.read_heif(f.read())
        img = Image.frombytes(heif.mode, heif.size, heif.data, "raw")
        out = os.path.splitext(f.filename)[0] + ".jpg"
        save_path = os.path.join(UPLOAD_DIR, out)
        img.save(save_path, "JPEG", quality=90)
        saved_name = out
    else:
        save_path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(save_path)
        saved_name = f.filename
    return f"/uploads/{saved_name}", 201