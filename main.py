# main.py — 관리자/업로드 제거, Supabase 방명록 + 정적 갤러리(최대 12장)
import os
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for
from supabase import create_client

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me")  # 환경변수로 바꿔 쓰는 걸 권장

# ===== Supabase 설정 =====
SUPABASE_URL = os.environ["SUPABASE_URL"]
# 서버 전용이면 SERVICE_ROLE 키 추천(노출 주의). 없으면 ANON 키 사용.
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== 경로/상수 =====
BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"
GALLERY_DIR = STATIC_DIR / "gallery"             # 정적 갤러리 폴더
MAIN_PHOTO_PATH = STATIC_DIR / "garu-main.jpg"   # 메인 대표 이미지 (정적 교체)

MAX_IMAGES = 12
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
LEGACY_COUNT = 14  # 기존 방명록 개수 가산용(필요 없으면 0으로)

# ===== 방명록(DB) 유틸 =====
def db_list_guestbook(limit: int = 200):
    """Supabase guestbook 테이블에서 최신순 조회"""
    res = (
        supabase.table("guestbook")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []

def db_insert_guestbook(name: str, message: str):
    supabase.table("guestbook").insert({"name": name, "message": message}).execute()

def normalize_rows(rows):
    """
    템플릿 호환을 위해 DB 로우를 {name, message, date} 형태로 변환
    created_at(ISO) → 'YYYY-MM-DD HH:MM' 문자열
    """
    out = []
    for r in rows:
        iso = r.get("created_at") or ""
        date = ""
        if isinstance(iso, str) and "T" in iso:
            # 예: 2025-10-24T09:15:00Z → 2025-10-24 09:15
            date = iso.replace("T", " ")[:16].replace("Z", "")
        out.append({"name": r.get("name", ""), "message": r.get("message", ""), "date": date})
    return out

# ===== 정적 갤러리 유틸 =====
def get_gallery_images():
    """static/gallery/ 에 있는 이미지들만 읽어 최대 12장 전시"""
    if not GALLERY_DIR.is_dir():
        return []
    files = [
        p.name for p in sorted(GALLERY_DIR.glob("*"))
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ][:MAX_IMAGES]
    return [{"url": url_for("static", filename=f"gallery/{name}"), "name": name} for name in files]

# ===== 메인 이미지 캐시버스터(선택) =====
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
    # 템플릿에서: {{ url_for('static', filename='garu-main.jpg') }}?v={{ ver_static('garu-main.jpg') }}
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

# ===== 개발용 실행 =====
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)