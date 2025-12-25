# app.py — 정적 운영(깃으로 사진만 교체) 버전
import os
from pathlib import Path
from flask import Flask, render_template, url_for

app = Flask(__name__, static_folder="static", template_folder="templates")

# ----------------------------
# 정적 갤러리 설정
# ----------------------------
MAX_IMAGES = 12  # 최대 12장 전시

def get_gallery_images():
    """
    static/gallery/ 폴더에 있는 이미지들을 읽어
    최대 12장까지 전시용 리스트로 반환합니다.
    """
    folder = Path(app.static_folder) / "gallery"
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    files = [p.name for p in sorted(folder.glob("*")) if p.suffix.lower() in exts]
    files = files[:MAX_IMAGES]
    return [
        {"url": url_for("static", filename=f"gallery/{name}"), "name": name}
        for name in files
    ]

# 갤러리 보기 전용 라우트
@app.get("/gallery")
def gallery():
    images = get_gallery_images()
    return render_template("gallery.html", images=images)

# ----------------------------
# (참고) 다른 페이지 라우트들
# ----------------------------
# 이미 index, guest_list 등이 있다면 그대로 두세요.
# 예시:
# @app.get("/")
# def index():
#     return render_template("index.html")
#
# @app.get("/guest")
# def guest_list():
#     return render_template("guest_list.html")

# ----------------------------
# 개발용 실행
# ----------------------------
if __name__ == "__main__":
    # 로컬 개발 시 편의를 위한 설정 (Render 배포에는 영향 없음)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)