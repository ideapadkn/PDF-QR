from flask import Flask, request, redirect, render_template, send_from_directory, session, url_for
import os
import qrcode
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.secret_key = 'very_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'pdfs')
QR_FOLDER = os.path.join('static', 'qr')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# Пользователи
USERS = {
    "admin": "admin123",
    "client": "client123"
}

@app.before_request
def require_login():
    public_paths = ["/login", "/logout"]
    if (
        request.path.startswith("/static/")
        or request.path.startswith("/view/")
        or any(request.path.startswith(p) for p in public_paths)
    ):
        return  # Разрешить доступ

    if not session.get("logged_in"):
        return redirect("/login")

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def admin_panel():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template("admin.html", files=files, username=session.get("username"))

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "pdf_file" not in request.files:
        return "Файл не найден", 400
    file = request.files["pdf_file"]
    if not file.filename.endswith(".pdf"):
        return "Нужен PDF-файл", 400

    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # Генерация публичной ссылки и QR
    public_url = url_for('view_pdf', filename=filename, _external=True)

    qr_img = qrcode.make(public_url).convert("RGB")

    # Вставляем QR в PDF (на отдельной первой странице)
    qr_pdf_io = BytesIO()
    c = canvas.Canvas(qr_pdf_io, pagesize=letter)
    c.drawString(100, 720, "Сканируй QR-код, чтобы открыть PDF онлайн:")
    c.drawInlineImage(qr_img, 100, 500, width=200, height=200)
    c.showPage()
    c.save()
    qr_pdf_io.seek(0)

    original = PdfReader(filepath)
    output = PdfWriter()
    qr_page = PdfReader(qr_pdf_io).pages[0]
    output.add_page(qr_page)
    for page in original.pages:
        output.add_page(page)

    with open(filepath, "wb") as f_out:
        output.write(f_out)

    # Сохраняем QR PNG для админки
    qr_path = os.path.join(QR_FOLDER, filename + ".png")
    qr_img.save(qr_path)

    return redirect("/")

@app.route("/delete/<filename>", methods=["POST"])
def delete_pdf(filename):
    os.remove(os.path.join(UPLOAD_FOLDER, filename))
    qr_file = os.path.join(QR_FOLDER, filename + ".png")
    if os.path.exists(qr_file):
        os.remove(qr_file)
    return redirect("/")

@app.route("/rename/<filename>", methods=["POST"])
def rename_pdf(filename):
    new_name = request.form.get("new_name", "").strip()
    if not new_name.endswith(".pdf"):
        new_name += ".pdf"
    old_pdf = os.path.join(UPLOAD_FOLDER, filename)
    new_pdf = os.path.join(UPLOAD_FOLDER, new_name)
    os.rename(old_pdf, new_pdf)

    old_qr = os.path.join(QR_FOLDER, filename + ".png")
    new_qr = os.path.join(QR_FOLDER, new_name + ".png")
    if os.path.exists(old_qr):
        os.rename(old_qr, new_qr)

    return redirect("/")

@app.route("/pdfs/<filename>")
def get_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/view/<filename>")
def view_pdf(filename):
    return render_template("viewer.html", filename=filename)

if __name__ == "__main__":
    app.run(debug=True)
