from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import datetime, os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change-me"  # flash 메시지 용. 원하면 변경하세요.

# ===== 경로/설정 =====
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "guestbook.json")
LEGACY_COUNT = 14

STATIC_DIR = "static"
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")   # 업로드 저장 폴더
GALLERY_DIR = os.path.join(STATIC_DIR, "gallery")  # 초기 샘플 사진 폴더(없어도 OK)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
# GALLERY_DIR은 있으면 사용

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

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
    """
    dir_path의 이미지를 허용 확장자만 모아 최신 수정시간 내림차순으로 정렬.
    템플릿에서 바로 <img src>로 쓸 수 있게 web 경로(/static/...)를 넣어 반환.
    """
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
            "url": f"/{web_prefix.strip('/')}/{name}",  # 예: /static/uploads/xxx.jpg
            "mtime": mtime,
            "name": name,
        })
    items.sort(key=lambda x: x["mtime"], reverse=True)
    # 템플릿에선 url만 쓰니 url 리스트로 변경
    return [x["url"] for x in items]

# ===== 라우팅 =====
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

# ===== 갤러리 페이지 =====
@app.route("/gallery", endpoint="gallery")
def gallery():
    """
    /static/uploads(업로드) + /static/gallery(샘플, 있을 때만)를 합쳐 최신순으로 보여줌.
    """
    uploaded = list_images_from(UPLOAD_DIR, "static/uploads")
    samples = list_images_from(GALLERY_DIR, "static/gallery")
    images = uploaded + samples
    return render_template("gallery.html", images=images)

# ===== 업로드 (GET: 폼, POST: 저장) =====
@app.route("/gallery/upload", methods=["GET", "POST"], endpoint="gallery_upload")
def gallery_upload():
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
    saved_name = f"{ts}_{name}{ext.lower()}"
    file.save(os.path.join(UPLOAD_DIR, saved_name))

    flash("업로드 완료!")
    return redirect(url_for("gallery"))

# (선택) 업로드 파일 직접 서빙이 필요할 때만 사용
# 현재는 /static/uploads 경로를 사용하므로 보통 필요 없음.
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    # 개발 중이면 debug=True로 에러 상세 확인 가능
    app.run(debug=True, use_reloader=False)