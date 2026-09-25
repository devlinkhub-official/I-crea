# ==============================================================================
# File: main.py
# Description: SchoolSync - 学校・保護者連絡システム (一から再構築版)
# Dependencies: fastapi, uvicorn
# Command: python main.py
# ==============================================================================

import sqlite3
from typing import Optional
from fastapi import FastAPI, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="SchoolSync")
DB_NAME = "schoolsync.db"

# ------------------------------------------------------------------------------
# 1. データベース初期化・操作関数
# ------------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベースとテーブルの作成、初期データの投入"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # ユーザーテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student'
            )
        """)
        
        # お便りテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS otayori (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                sender TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 初期アカウント（teacher / student）の存在確認と作成
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('teacher', 'password123', 'teacher')")
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('student', 'password123', 'student')")
        
        # 初期お便りデータの存在確認と作成
        cursor.execute("SELECT COUNT(*) FROM otayori")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO otayori (title, content, sender) VALUES (?, ?, ?)",
                ("学級だより 4月号", "新学期が始まりました。今年度もよろしくお願いします。", "学校事務局")
            )
        
        conn.commit()

# アプリ起動時にDB初期化を実行
init_db()

# ------------------------------------------------------------------------------
# 2. リクエストの型定義 (Pydantic)
# ------------------------------------------------------------------------------
class UserAuth(BaseModel):
    username: str
    password: str
    role: Optional[str] = "student"

class OtayoriCreate(BaseModel):
    title: str
    content: str
    sender: str

# ------------------------------------------------------------------------------
# 3. API エンドポイント (Controller)
# ------------------------------------------------------------------------------
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=HTML_BODY)

@app.post("/api/signup")
def signup(user: UserAuth):
    u = user.username.strip()
    p = user.password.strip()
    r = user.role.strip() if user.role else "student"

    if not u or not p:
        return {"success": False, "message": "ユーザー名とパスワードを入力してください"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (u,))
        if cursor.fetchone():
            return {"success": False, "message": "このユーザー名はすでに使われています"}
        
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, p, r))
        conn.commit()

    return {"success": True, "message": f"アカウント「{u}」を作成しました！ログインしてください。"}

@app.post("/api/login")
def login(user: UserAuth):
    u = user.username.strip()
    p = user.password.strip()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (u, p))
        row = cursor.fetchone()

    if row:
        return {
            "success": True,
            "message": "ログインに成功しました",
            "username": row["username"],
            "role": row["role"]
        }
    return {"success": False, "message": "ユーザー名またはパスワードが正しくありません"}

@app.get("/api/otayori")
def list_otayori():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM otayori ORDER BY id DESC")
        items = [dict(row) for row in cursor.fetchall()]
    return {"success": True, "items": items}

@app.post("/api/otayori")
def create_otayori(item: OtayoriCreate):
    t = item.title.strip()
    c = item.content.strip()
    s = item.sender.strip()

    if not t or not c:
        return {"success": False, "message": "タイトルと本文は必須です"}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO otayori (title, content, sender) VALUES (?, ?, ?)", (t, c, s))
        conn.commit()

    return {"success": True, "message": "お便りを投稿しました"}

# ------------------------------------------------------------------------------
# 4. フロントエンド画面 (HTML / CSS / JavaScript)
# ------------------------------------------------------------------------------
HTML_BODY = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SchoolSync</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { margin: 0; background-color: #f0f2f5; color: #1c1e21; }
        header { background: #1877f2; color: white; text-align: center; padding: 1rem; }
        .container { max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .alert { padding: 0.8rem; border-radius: 6px; margin-bottom: 1rem; display: none; font-weight: bold; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; margin-bottom: 0.3rem; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 0.6rem; border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; }
        button { border: none; padding: 0.7rem 1.2rem; border-radius: 6px; font-size: 1rem; cursor: pointer; font-weight: bold; }
        .btn-primary { background: #1877f2; color: white; }
        .btn-primary:hover { background: #166fe5; }
        .btn-success { background: #42b72a; color: white; }
        .btn-success:hover { background: #36a420; }
        .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 1rem; }
        .tab { padding: 0.5rem 1rem; cursor: pointer; font-weight: bold; color: #65676b; }
        .tab.active { color: #1877f2; border-bottom: 2px solid #1877f2; margin-bottom: -2px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }
        .otayori-item { padding: 0.8rem; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; }
        .otayori-item:hover { background: #f8f9fa; }
        .hidden { display: none !important; }
        .user-badge { background: #e4e6eb; padding: 0.3rem 0.6rem; border-radius: 12px; font-size: 0.85rem; }
    </style>
</head>
<body>

    <header>
        <h1>SchoolSync</h1>
        <p>学校・保護者情報連絡ポータル</p>
    </header>

    <div class="container">
        <!-- 通知メッセージ表示エリア -->
        <div id="alert-box" class="alert"></div>

        <!-- ================= 認証セクション (ログイン / アカウント作成) ================= -->
        <div id="auth-section" class="card">
            <div class="tabs">
                <div id="tab-login" class="tab active" onclick="switchTab('login')">ログイン</div>
                <div id="tab-signup" class="tab" onclick="switchTab('signup')">新規アカウント作成</div>
            </div>

            <!-- ログインフォーム -->
            <div id="form-login">
                <div class="form-group">
                    <label>ユーザー名</label>
                    <input type="text" id="login-username" value="teacher" placeholder="ユーザー名を入力">
                </div>
                <div class="form-group">
                    <label>パスワード</label>
                    <input type="password" id="login-password" value="password123" placeholder="パスワードを入力">
                </div>
                <button class="btn-primary" onclick="doLogin()">ログイン</button>
            </div>

            <!-- サインアップフォーム -->
            <div id="form-signup" class="hidden">
                <div class="form-group">
                    <label>ユーザー名</label>
                    <input type="text" id="signup-username" placeholder="例: yamada">
                </div>
                <div class="form-group">
                    <label>パスワード</label>
                    <input type="password" id="signup-password" placeholder="パスワードを設定">
                </div>
                <div class="form-group">
                    <label>役割</label>
                    <select id="signup-role">
                        <option value="student">保護者・生徒</option>
                        <option value="teacher">教職員 (先生)</option>
                    </select>
                </div>
                <button class="btn-success" onclick="doSignup()">アカウントを作成する</button>
            </div>
        </div>

        <!-- ================= メイン機能セクション (ログイン後表示) ================= -->
        <div id="app-section" class="hidden">
            <!-- ユーザー情報ヘッダー -->
            <div class="card" style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    ようこそ <strong id="display-user"></strong> 様 
                    <span id="display-role" class="user-badge"></span>
                </div>
                <button style="background: #e4e6eb; color: #333;" onclick="doLogout()">ログアウト</button>
            </div>

            <!-- お便り閲覧エリア -->
            <div class="grid">
                <div class="card">
                    <h3>お便り一覧</h3>
                    <div id="otayori-list">読み込み中...</div>
                </div>
                <div class="card">
                    <h3>詳細内容</h3>
                    <div id="otayori-detail" style="color: #65676b;">左の一覧からお便りを選択してください。</div>
                </div>
            </div>

            # 投稿フォーム（教職員のみに表示）
            <div id="post-section" class="card hidden">
                <h3>新規お便りを投稿</h3>
                <div class="form-group">
                    <label>タイトル</label>
                    <input type="text" id="post-title" placeholder="例: 体育祭のお知らせ">
                </div>
                <div class="form-group">
                    <label>差出人名</label>
                    <input type="text" id="post-sender" value="学校事務局">
                </div>
                <div class="form-group">
                    <label>本文</label>
                    <textarea id="post-content" rows="4" placeholder="詳細を入力してください"></textarea>
                </div>
                <button class="btn-success" onclick="doPostOtayori()">お便りを送信する</button>
            </div>
        </div>
    </div>

    <script>
        let currentUser = null;

        // メッセージ表示関数
        function showAlert(msg, isSuccess) {
            const box = document.getElementById("alert-box");
            box.textContent = msg;
            box.className = `alert ${isSuccess ? 'alert-success' : 'alert-error'}`;
            box.style.display = "block";
            setTimeout(() => { box.style.display = "none"; }, 5000);
        }

        // タブ切り替え処理
        function switchTab(type) {
            document.getElementById("tab-login").classList.toggle("active", type === 'login');
            document.getElementById("tab-signup").classList.toggle("active", type === 'signup');
            document.getElementById("form-login").classList.toggle("hidden", type !== 'login');
            document.getElementById("form-signup").classList.toggle("hidden", type !== 'signup');
        }

        // ログイン処理
        async function doLogin() {
            const u = document.getElementById("login-username").value;
            const p = document.getElementById("login-password").value;

            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: u, password: p })
            });
            const data = await res.json();

            if (data.success) {
                currentUser = { username: data.username, role: data.role };
                showAlert(data.message, true);
                showAppUI();
            } else {
                showAlert(data.message, false);
            }
        }

        // サインアップ（アカウント作成）処理
        async function doSignup() {
            const u = document.getElementById("signup-username").value;
            const p = document.getElementById("signup-password").value;
            const r = document.getElementById("signup-role").value;

            const res = await fetch("/api/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: u, password: p, role: r })
            });
            const data = await res.json();

            if (data.success) {
                showAlert(data.message, true);
                document.getElementById("login-username").value = u;
                document.getElementById("login-password").value = p;
                document.getElementById("signup-username").value = "";
                document.getElementById("signup-password").value = "";
                switchTab('login');
            } else {
                showAlert(data.message, false);
            }
        }

        // ログイン後のUI制御
        function showAppUI() {
            document.getElementById("auth-section").classList.add("hidden");
            document.getElementById("app-section").classList.remove("hidden");

            document.getElementById("display-user").textContent = currentUser.username;
            document.getElementById("display-role").textContent = currentUser.role === 'teacher' ? '教職員' : '保護者・生徒';

            // 先生権限のみ投稿フォームを表示
            if (currentUser.role === 'teacher') {
                document.getElementById("post-section").classList.remove("hidden");
            } else {
                document.getElementById("post-section").classList.add("hidden");
            }

            loadOtayori();
        }

        // ログアウト処理
        function doLogout() {
            currentUser = null;
            document.getElementById("app-section").classList.add("hidden");
            document.getElementById("auth-section").classList.remove("hidden");
            showAlert("ログアウトしました", true);
        }

        // お便り一覧の取得と表示
        async function loadOtayori() {
            const res = await fetch("/api/otayori");
            const data = await res.json();
            const listContainer = document.getElementById("otayori-list");

            if (data.success && data.items.length > 0) {
                listContainer.innerHTML = "";
                data.items.forEach(item => {
                    const div = document.createElement("div");
                    div.className = "otayori-item";
                    div.innerHTML = `<strong>${item.title}</strong><br><small style="color:#65676b;">${item.sender} ・ ${item.created_at}</small>`;
                    div.onclick = () => showDetail(item);
                    listContainer.appendChild(div);
                });
            } else {
                listContainer.innerHTML = "<p>お便りはありません。</p>";
            }
        }

        // お便り詳細の表示
        function showDetail(item) {
            document.getElementById("otayori-detail").innerHTML = `
                <h2 style="margin-top:0;">${item.title}</h2>
                <p style="color:#65676b;"><strong>差出人:</strong> ${item.sender} | <strong>投稿日時:</strong> ${item.created_at}</p>
                <hr style="border:0; border-top:1px solid #eee;">
                <p style="white-space: pre-wrap; line-height: 1.6;">${item.content}</p>
            `;
        }

        // お便り投稿処理
        async function doPostOtayori() {
            const t = document.getElementById("post-title").value;
            const s = document.getElementById("post-sender").value;
            const c = document.getElementById("post-content").value;

            const res = await fetch("/api/otayori", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: t, sender: s, content: c })
            });
            const data = await res.json();

            if (data.success) {
                showAlert(data.message, true);
                document.getElementById("post-title").value = "";
                document.getElementById("post-content").value = "";
                loadOtayori();
            } else {
                showAlert(data.message, false);
            }
        }
    </script>
</body>
</html>
"""

# ------------------------------------------------------------------------------
# 5. アプリ起動処理
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)