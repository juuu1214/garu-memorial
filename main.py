from flask import Flask, render_template, request, redirect, url_for, abort, flash
import datetime, os, json, uuid, hashlib

app = Flask(__name__)
app.secret_key = "change-me"  # flash 메시지용. 환경변수로 빼도 됨.

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "guestbook.json")
LEGACY_COUNT = 14  # 하드코딩된 예전 방명록 개수

def load_guestbook():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    # 마이그레이션: id 없는 기존 항목에 id 부여
    changed = False
    for item in data:
        if "id" not in item:
            item["id"] = uuid.uuid4().hex
            changed = True
    if changed:
        save_guestbook(data)
    return data

def save_guestbook(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def hash_pw(pw: str) -> str:
    # 빈 문자열은 저장하지 않음
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def find_entry(data, entry_id):
    for i, item in enumerate(data):
        if item.get("id") == entry_id:
            return i, item
    return None, None

@app.route('/')
def index():
    gb = load_guestbook()
    return render_template('index.html', guestbook=gb)

@app.route('/guest-list', endpoint='guest_list')
def guest_list():
    gb = load_guestbook()
    total_count = len(gb) + LEGACY_COUNT
    return render_template('guest_list.html', guestbook=gb, total_count=total_count)

@app.route('/write', methods=['POST'], endpoint='write')
def write():
    name = request.form.get('name', '').strip()
    message = request.form.get('message', '').strip()
    pw = (request.form.get('password') or '').strip()
    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if name and message:
        gb = load_guestbook()
        entry = {
            "id": uuid.uuid4().hex,
            "name": name,
            "message": message,
            "date": date
        }
        if pw:
            entry["password_hash"] = hash_pw(pw)
        gb.insert(0, entry)  # 최신이 위로
        save_guestbook(gb)

    return redirect(url_for('guest_list'))

@app.route('/guest/create', methods=['GET'], endpoint='guest_create')
def guest_create():
    return render_template('guest_create.html')

# ====== 새로 추가: 편집 페이지, 수정, 삭제 ======

@app.route('/guest/edit', methods=['GET'], endpoint='guest_edit')
def guest_edit():
    """
    예시 URL과 비슷하게 ?messageId=... 쿼리로 받는다.
    (원하면 path 파라미터로 바꿔도 됨)
    """
    entry_id = request.args.get('messageId') or request.args.get('id')
    if not entry_id:
        abort(400, description="messageId가 없습니다.")
    gb = load_guestbook()
    _, entry = find_entry(gb, entry_id)
    if not entry:
        abort(404, description="해당 글을 찾을 수 없습니다.")
    return render_template('guest_edit.html', entry=entry)

@app.route('/guest/update', methods=['POST'], endpoint='guest_update')
def guest_update():
    entry_id = request.form.get('id')
    name = request.form.get('name', '').strip()
    message = request.form.get('message', '').strip()
    pw = (request.form.get('password') or '').strip()

    gb = load_guestbook()
    idx, entry = find_entry(gb, entry_id)
    if entry is None:
        abort(404, description="해당 글을 찾을 수 없습니다.")

    # 비밀번호 검증 (설정된 경우에만)
    stored = entry.get('password_hash')
    if stored:
        if not pw or hash_pw(pw) != stored:
            flash("비밀번호가 올바르지 않습니다.", "error")
            return redirect(url_for('guest_edit', messageId=entry_id))

    # 업데이트
    if name:
        entry['name'] = name
    if message:
        entry['message'] = message
    entry['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")  # 수정시간으로 업데이트(선택)
    gb[idx] = entry
    save_guestbook(gb)
    flash("수정되었습니다.", "success")
    return redirect(url_for('guest_list'))

@app.route('/guest/delete', methods=['POST'], endpoint='guest_delete')
def guest_delete():
    entry_id = request.form.get('id')
    pw = (request.form.get('password') or '').strip()

    gb = load_guestbook()
    idx, entry = find_entry(gb, entry_id)
    if entry is None:
        abort(404, description="해당 글을 찾을 수 없습니다.")

    stored = entry.get('password_hash')
    if stored:
        if not pw or hash_pw(pw) != stored:
            flash("비밀번호가 올바르지 않습니다.", "error")
            return redirect(url_for('guest_edit', messageId=entry_id))

    # 삭제
    gb.pop(idx)
    save_guestbook(gb)
    flash("삭제되었습니다.", "success")
    return redirect(url_for('guest_list'))

# (디버그용 라우트는 필요시 유지)
@app.route("/_routes")
def _routes():
    lines = []
    for r in app.url_map.iter_rules():
        lines.append(f"{r.endpoint:20s} {','.join(sorted(r.methods)):<20s} {r.rule}")
    return "<pre>" + "\n".join(sorted(lines)) + "</pre>"

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)