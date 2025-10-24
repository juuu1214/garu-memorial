# main.py — 관리자/업로드 제거, 정적 갤러리(최대 12장) 버전
import os
import json
import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")  # 필요시 환경변수로 설정

# ===== 경로/설정 =====
BASE_DIR = Path(__file__).parent.resolve()

DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "guestbook.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = BASE_DIR / "static"
GALLERY_DIR = STATIC_DIR / "gallery"             # 정적 갤러리 폴더
MAIN_PHOTO_PATH = STATIC_DIR / "garu-main.jpg"   # 메인 대표 이미지

MAX_IMAGES = 12
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
LEGACY_COUNT = 14  # 기존 방명록 개수 가산용(선택)

# ===== 유틸 =====
def load_guestbook():
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_guestbook(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_gallery_images():
    """static/gallery/ 에 있는 이미지들만 읽어 최대 12장 전시"""
    if not GALLERY_DIR.is_dir():
        return []
    files = [
        p.name for p in sorted(GALLERY_DIR.glob("*"))
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ][:MAX_IMAGES]
    return [{"url": url_for("static", filename=f"gallery/{name}"), "name": name} for name in files]

# 메인 이미지 캐시버스터 (교체 직후 반영)
@app.context_processor
def inject_versions():
    def ver_static(rel_path: str):
        p = STATIC_DIR / rel_path
        try:
            return int(p.stat().st_mtime)
        except Exception:
            return 0
    return {"ver_static": ver_static}

# ===== 페이지 =====
@app.route("/")
def index():
    gb = load_guestbook()
    # 템플릿에서: {{ url_for('static', filename='garu-main.jpg') }}?v={{ ver_static('garu-main.jpg') }}
    return render_template("index.html", guestbook=gb)

@app.route("/guest-list", endpoint="guest_list")
def guest_list():
    gb = load_guestbook()
    total_count = len(gb) + LEGACY_COUNT
    return render_template("guest_list.html", guestbook=gb, total_count=total_count)

@app.route("/guest/create", methods=["GET"], endpoint="guest_create")
def guest_create():
    return render_template("guest_create.html")

@app.route("/write", methods=["POST"])
def write():
    name = request.form.get("name", "").strip()
    message = request.form.get("message", "").strip()
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if name and message:
        gb = load_guestbook()
        gb.insert(0, {"name": name, "message": message, "date": date})
        save_guestbook(gb)
    return redirect(url_for("guest_list"))

@app.route("/gallery", endpoint="gallery")
def gallery():
    images = get_gallery_images()
    return render_template("gallery.html", images=images)

# ===== 개발용 실행 =====
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)