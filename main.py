from flask import (
    Flask, render_template, request, redirect, url_for,
    send_from_directory, flash, session
)
import datetime, os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change-me"  # 실서버에선 환경변수로 바꿔주세요

# ===== 경로/설정 =====
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "guestbook.json")
LEGACY_COUNT = 14

STATIC_DIR = "static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
GALLERY_DIR = os.path.join(STATIC_DIR, "gallery")   # 샘플 폴더(없어도 OK)
MAIN_PHOTO_PATH = os.path.join(STATIC_DIR, "garu-main.jpg")  # 메인 사진

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
# GALLERY_DIR은 있으면 사용

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic"}
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

# 🔐 어드민 비번 (환경변수 우선)
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "1234")


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


# ===== 이미지 수집 유틸 =====
def list_images_from(dir_path: str, web_prefix: str):
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
        })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items


# ===== 기본 페이지 =====
@app.route("/")
def index():
    gb = load_guestbook()
    # 메인 사진 캐시버스터
    img_ver = 0
    if os.path.exists(MAIN_PHOTO_PATH):
        try:
            img_ver = int(os.path.getmtime(MAIN_PHOTO_PATH))
        except Exception:
            img_ver = 0
    return render_template("index.html", guestbook=gb, img_ver=img_ver)

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


# ===== 갤러리 =====
@app.route("/gallery", endpoint="gallery")
def gallery():
    # 업로드 + (있다면) 샘플 합쳐서 최신순
    uploaded = list_images_from(UPLOAD_DIR, "static/uploads")
    samples = list_images_from(GALLERY_DIR, "static/gallery")
    images = uploaded + samples
    return render_template("gallery.html", images=images)

@app.route("/upload", methods=["GET", "POST"], endpoint="upload")
def upload():
    # 업로드는 어드민만 허용
    if not session.get("is_admin"):
        flash("권한이 없습니다.")
        return redirect(url_for("admin"))

    if request.method == "GET":
        return render_template("upload.html")

    file = request.files.get("photo")
    if not file or file.filename == "":
        flash("파일을 선택해 주세요.")
        return redirect(url_for("upload"))

    if not allowed_file(file.filename):
        flash("허용되지 않는 파일 형식입니다. (png, jpg, jpeg, gif, webp)")
        return redirect(url_for("upload"))

    filename = secure_filename(file.filename)
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    name, ext = os.path.splitext(filename)
    saved_name = f"{ts}_{name}{ext}"
    file.save(os.path.join(UPLOAD_DIR, saved_name))
    flash("업로드 완료!")
    return redirect(url_for("admin"))  # 업로드 후 어드민으로


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # 정적파일 제공 (업로드 폴더)
    return send_from_directory(UPLOAD_DIR, filename)


# ===== 어드민 전용 페이지/행동 =====
@app.route("/admin", methods=["GET"])
def admin():
    # 어드민 대시보드(로그인 전/후 한 페이지에서 처리)
    uploaded = list_images_from(UPLOAD_DIR, "static/uploads")
    # 샘플은 삭제 못 하게, 대시보드에는 참고용으로만 보여주고 싶다면 포함/제외 선택
    return render_template("admin.html", images=uploaded)

@app.post("/admin/login")
def admin_login():
    pw = request.form.get("password", "")
    if pw == ADMIN_PASSWORD:
        session["is_admin"] = True
        flash("관리자 로그인 완료!")
    else:
        flash("비밀번호가 올바르지 않습니다.")
    return redirect(url_for("admin"))

@app.post("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("로그아웃 했습니다.")
    return redirect(url_for("admin"))

@app.post("/admin/main-photo", endpoint="admin_main_photo")
def admin_main_photo():
    if not session.get("is_admin"):
        flash("권한이 없습니다.")
        return redirect(url_for("admin"))

    file = request.files.get("photo")
    if not file or file.filename == "":
        flash("사진 파일을 선택해 주세요.")
        return redirect(url_for("admin"))

    if not allowed_file(file.filename):
        flash("허용되지 않는 파일 형식입니다.")
        return redirect(url_for("admin"))

    tmp_path = MAIN_PHOTO_PATH + ".tmp"
    file.save(tmp_path)
    os.replace(tmp_path, MAIN_PHOTO_PATH)  # 원자적 교체
    flash("메인 사진을 변경했습니다.")
    return redirect(url_for("admin"))

@app.post("/admin/gallery/delete", endpoint="admin_gallery_delete")
def admin_gallery_delete():
    # 업로드 폴더의 파일만 삭제 허용 (샘플 폴더 X)
    if not session.get("is_admin"):
        flash("권한이 없습니다.")
        return redirect(url_for("admin"))

    filename = request.form.get("filename", "")
    if not filename:
        flash("삭제할 파일명이 없습니다.")
        return redirect(url_for("admin"))

    # 디렉터리 탈출 방지
    safe_name = secure_filename(filename)
    target_path = os.path.join(UPLOAD_DIR, safe_name)

    if not (os.path.isfile(target_path) and target_path.startswith(os.path.abspath(UPLOAD_DIR))):
        flash("삭제할 수 없는 대상입니다.")
        return redirect(url_for("admin"))

    try:
        os.remove(target_path)
        flash("사진을 삭제했습니다.")
    except Exception as e:
        flash(f"삭제 중 오류: {e}")

    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)