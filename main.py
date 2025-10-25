# main.py — Supabase 연동 + 방명록 + 정적 갤러리 (클린 버전)
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")

# ===== Supabase 설정 =====
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_ANON_KEY")
)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== 경로/상수 =====
BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"
GALLERY_DIR = STATIC_DIR / "gallery"
MAIN_PHOTO_PATH = STATIC_DIR / "garu-main.jpg"

MAX_IMAGES = 12
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
LEGACY_COUNT = 14

# ===== 방명록 DB 유틸 =====
def db_list_guestbook(limit: int = 200):
    """Supabase guestbook 테이블에서 최신순 조회"""
    res = (
        supabase.table("guestbook")
        .select("id,name,message,created_at")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []

def db_insert_guestbook(name: str, message: str):
    supabase.table("guestbook").insert({"name": name, "message": message}).execute()

def normalize_rows(rows):
    """created_at(UTC ISO) → KST 'YYYY-MM-DD HH:MM'"""
    kst = ZoneInfo("Asia/Seoul")
    out = []
    for r in rows:
        iso = r.get("created_at") or ""
        date_str = ""
        try:
            dt_utc = datetime.fromisoformat(iso.replace("Z", "+00:00"))
            dt_kst = dt_utc.astimezone(kst)
            date_str = dt_kst.strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_str = iso.replace("T", " ").replace("Z", "")[:16]
        out.append(
            {
                "name": r.get("name", ""),
                "message": r.get("message", ""),
                "date": date_str,
            }
        )
    return out

# ===== 갤러리 =====
def get_gallery_images():
    """static/gallery/ 내 이미지 최대 12장"""
    if not GALLERY_DIR.is_dir():
        return []
    files = [
        p.name
        for p in sorted(GALLERY_DIR.glob("*"))
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ][:MAX_IMAGES]
    return [{"url": url_for("static", filename=f"gallery/{name}"), "name": name} for name in files]

# ===== 캐시버스터 =====
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
    gb_rows = db_list_guestbook()
    gb = normalize_rows(gb_rows)
    return render_template("index.html", guestbook=gb)

@app.route("/guest-list", endpoint="guest_list")
def guest_list():
    gb_rows = db_list_guestbook()
    gb = normalize_rows(gb_rows)
    total_count = len(gb) + LEGACY_COUNT
    return render_template("guest_list.html", guestbook=gb, total_count=total_count)

@app.route("/guest/create", methods=["GET"], endpoint="guest_create")
def guest_create():
    return render_template("guest_create.html")

@app.route("/write", methods=["POST"])
def write():
    name = request.form.get("name", "").strip()
    message = request.form.get("message", "").strip()
    if name and message:
        db_insert_guestbook(name, message)
    return redirect(url_for("guest_list"))

@app.route("/gallery", endpoint="gallery")
def gallery():
    images = get_gallery_images()
    return render_template("gallery.html", images=images)

@app.get("/ping")
def ping():
    return "ok", 200

# ===== 캐시 비활성(즉시 반영용) =====
@app.after_request
def add_no_cache_headers(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# ===== 개발용 =====
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)