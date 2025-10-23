from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, flash, session
)
import datetime, os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change-me"  # flash, session 등에 필요. 원하면 안전한 값으로 변경하세요.

# ===== 설정 =====
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "guestbook.json")
LEGACY_COUNT = 14

STATIC_DIR = "static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
GALLERY_DIR = os.path.join(STATIC_DIR, "gallery")  # 샘플 폴더(있으면 사용)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

# ✅ 관리자 비밀번호 (환경변수로도 설정 가능)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ===== 방명록 유틸 =====
def load_guestbook():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_guestbook(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ===== 이미지 리스트 유틸 =====
def list_images_from(dir_path: str, web_prefix: str):
    """폴더가 없으면 빈 리스트, 있으면 허용 확장자만 가져와 최신순 정렬."""
    if not os.path.isdir(dir_path):
        return []
    items = []
    for name in os.listdir(dir_path):
        path = os.path.join(dir_path, name)
        if not os.path.isfile(path):
            continue
        if not allowed_file(name):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        items.append({
            "url": f"/{web_prefix}/{name}",  # 예: /static/uploads/xxx.jpg
            "mtime": mtime,
            "name": name,
            "origin": web_prefix,           # 어디 폴더에서 왔는지 표시
        })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


# ===== 템플릿에서 is_admin 사용 가능하게 =====
@app.context_processor
def inject_is_admin():
    return {"is_admin": bool(session.get("is_admin"))}


# ===== 라우트 =====
@app.route("/")
def index():
    gb = load_guestbook()
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


# ===== 관리자 로그인/로그아웃 =====
@app.route("/admin/login", methods=["GET", "POST"], endpoint="admin_login")
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")
    password = request.form.get("password", "")
    if password == ADMIN_PASSWORD:
        session["is_admin"] = True
        flash("관리자 로그인 완료!")
        # 직전 페이지로 돌아가고 싶으면 next를 사용
        next_url = request.args.get("next") or url_for("gallery")
        return redirect(next_url)
    flash("비밀번호가 올바르지 않습니다.")
    return redirect(url_for("admin_login"))


@app.route("/admin/logout", endpoint="admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("로그아웃 되었습니다.")
    return redirect(url_for("gallery"))


def require_admin():
    if not session.get("is_admin"):
        # 미로그인 시 로그인 페이지로 유도
        return redirect(url_for("admin_login", next=request.path))
    return None


# ===== 업로드 (관리자만) =====
@app.route("/upload", methods=["GET", "POST"], endpoint="gallery_upload")
def gallery_upload():
    # 권한 체크
    need = require_admin()
    if need:
        return need

    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("photo")
    if not file or file.filename == "":
        flash("파일을 선택해 주세요.")
        return redirect(url_for("gallery_upload"))

    if not allowed_file(file.filename):
        flash("허용되지 않는 파일 형식입니다. (png, jpg, jpeg, gif, webp)")
        return redirect(url_for("gallery_upload"))

    filename = secure_filename(file.filename)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    name, ext = os.path.splitext(filename)
    saved_name = f"{ts}_{name}{ext}"
    file.save(os.path.join(UPLOAD_DIR, saved_name))
    flash("업로드 완료!")
    return redirect(url_for("gallery"))


# ===== 이미지 삭제 (관리자만) =====
@app.route("/gallery/delete", methods=["POST"], endpoint="gallery_delete")
def gallery_delete():
    # 권한 체크
    need = require_admin()
    if need:
        return need

    filename = request.form.get("filename", "")
    if not filename:
        flash("잘못된 요청입니다.")
        return redirect(url_for("gallery"))

    # 업로드 폴더의 파일만 삭제 허용 (샘플 폴더 삭제 금지)
    target_path = os.path.join(UPLOAD_DIR, filename)
    # 디렉터리 탈출 방지
    if not os.path.abspath(target_path).startswith(os.path.abspath(UPLOAD_DIR)):
        flash("삭제 권한이 없습니다.")
        return redirect(url_for("gallery"))

    if os.path.exists(target_path):
        try:
            os.remove(target_path)
            flash("사진을 삭제했습니다.")
        except Exception:
            flash("삭제 중 오류가 발생했습니다.")
    else:
        flash("파일을 찾을 수 없습니다.")
    return redirect(url_for("gallery"))


# ===== 정적 업로드 파일 접근 =====
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ===== 갤러리 페이지 =====
@app.route("/gallery", endpoint="gallery")
def gallery():
    uploaded = list_images_from(UPLOAD_DIR, "static/uploads")
    samples = list_images_from(GALLERY_DIR, "static/gallery")  # 없으면 빈 리스트
    images = uploaded + samples
    return render_template("gallery.html", images=images)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)