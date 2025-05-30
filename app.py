from flask import Flask, request, redirect, render_template, send_from_directory, session, url_for
import os
import base64

app = Flask(__name__)
app.secret_key = 'very_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'pdfs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Простая база пользователей
USERS = {
    "admin": "admin123",
    "client": "client123"
}

# === Авторизация доступа ===
@app.before_request
def require_login():
    public_paths = ["/login", "/logout"]
    if (
        request.path.startswith("/static/")
        or request.path.startswith("/view/")
        or request.path.startswith("/pdfs/")
        or any(request.path.startswith(p) for p in public_paths)
    ):
        return
    if not session.get("logged_in"):
        return redirect("/login")

# === Вход ===
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if USERS.get(username) == password:
            session["logged_in"] = True
            session["username"] = username
            return redirect("/")
        return "Неверные данные", 403
    return render_template("login.html")

# === Выход ===
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# === Шифрование и дешифрование имени файла ===
def encode_filename(filename):
    return base64.urlsafe_b64encode(filename.encode()).decode()

def decode_filename(encoded):
    # Добавим обратно padding (==), если не хватает
    padding = '=' * (-len(encoded) % 4)
    return base64.urlsafe_b64decode((encoded + padding).encode()).decode()

# === Главная страница админки ===
@app.route("/")
def admin_panel():
    files = os.listdir(UPLOAD_FOLDER)
    links = {f: encode_filename(f) for f in files if f.endswith(".pdf")}
    return render_template("admin.html", links=links, username=session.get("username"))

# === Загрузка PDF ===
@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "pdf_file" not in request.files:
        return "Файл не найден", 400

    file = request.files["pdf_file"]

    if not file.filename.endswith(".pdf"):
        return "Нужен PDF-файл", 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    return redirect("/")

# === Удаление PDF ===
@app.route("/delete/<filename>", methods=["POST"])
def delete_pdf(filename):
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, filename))
    except FileNotFoundError:
        pass
    return redirect("/")

# === Публичный просмотр PDF ===
@app.route("/view/<encoded>")
def view_pdf(encoded):
    try:
        filename = decode_filename(encoded)
        return render_template("viewer.html", filename=filename)
    except Exception:
        return "Неверная ссылка", 404

# === Получение PDF-файла для iframe ===
@app.route("/pdfs/<filename>")
def get_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True)
