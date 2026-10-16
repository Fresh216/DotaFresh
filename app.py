from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

app.secret_key = "dota_service_secret_key_12345"

DATABASE = "users.db"


# ==========================================================
# DATABASE
# ==========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # Создаём таблицу, если её ещё нет
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TEXT
        )
    """)

    # Проверяем наличие created_at
    columns = conn.execute(
        "PRAGMA table_info(users)"
    ).fetchall()

    column_names = [column["name"] for column in columns]

    # Если старой базе не хватает created_at,
    # добавляем колонку автоматически
    if "created_at" not in column_names:

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN created_at TEXT
        """)

        conn.commit()

    conn.close()


# ==========================================================
# ГЛАВНАЯ
# ==========================================================

@app.route("/")
def index():

    if "user_id" in session:
        return redirect(url_for("cabinet"))

    return render_template("index.html")


# ==========================================================
# РЕГИСТРАЦИЯ
# ==========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:
        return redirect(url_for("cabinet"))

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        password_repeat = request.form.get(
            "password_repeat", ""
        )

        # ------------------------------
        # Проверка заполнения
        # ------------------------------

        if not username or not email or not password or not password_repeat:

            flash("Заполните все поля")

            return render_template(
                "register.html",
                username=username,
                email=email
            )

        # ------------------------------
        # Проверка паролей
        # ------------------------------

        if password != password_repeat:

            flash("Пароли не совпадают")

            return render_template(
                "register.html",
                username=username,
                email=email
            )

        # ------------------------------
        # Проверка длины пароля
        # ------------------------------

        if len(password) < 6:

            flash(
                "Пароль должен содержать минимум 6 символов"
            )

            return render_template(
                "register.html",
                username=username,
                email=email
            )

        conn = get_db()

        # ------------------------------
        # Проверка ника
        # ------------------------------

        existing_username = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        if existing_username:

            conn.close()

            flash("Такой ник уже занят")

            return render_template(
                "register.html",
                username="",
                email=email
            )

        # ------------------------------
        # Проверка email
        # ------------------------------

        existing_email = conn.execute(
            """
            SELECT id
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()

        if existing_email:

            conn.close()

            flash("Такой email уже зарегистрирован")

            return render_template(
                "register.html",
                username=username,
                email=""
            )

        # ------------------------------
        # Хеширование пароля
        # ------------------------------

        password_hash = generate_password_hash(
            password
        )

        # ------------------------------
        # Дата регистрации
        # ------------------------------

        created_at = datetime.now().strftime(
            "%d.%m.%Y %H:%M"
        )

        # ------------------------------
        # Создание пользователя
        # ------------------------------

        conn.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                email,
                password_hash,
                created_at
            )
        )

        conn.commit()
        conn.close()

        flash(
            "Регистрация прошла успешно! Теперь войдите."
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ==========================================================
# ВХОД
# ==========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("cabinet"))

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

        conn.close()

        # Проверяем ник и пароль
        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            return redirect(
                url_for("cabinet")
            )

        flash(
            "Неверный ник или пароль"
        )

        return render_template(
            "login.html",
            username=username
        )

    return render_template(
        "login.html"
    )


# ==========================================================
# ЛИЧНЫЙ КАБИНЕТ
# ==========================================================

@app.route("/cabinet")
def cabinet():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    conn.close()

    if not user:

        session.clear()

        return redirect(
            url_for("login")
        )

    return render_template(
        "cabinet.html",
        user=user
    )


# ==========================================================
# ИЗМЕНЕНИЕ НИКА
# ==========================================================

@app.route(
    "/change_username",
    methods=["POST"]
)
def change_username():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    new_username = request.form.get(
        "new_username", ""
    ).strip()

    password = request.form.get(
        "username_password", ""
    )

    if not new_username:

        flash("Введите новый ник")

        return redirect(
            url_for("cabinet")
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    # Проверяем старый пароль
    if not check_password_hash(
        user["password"],
        password
    ):

        conn.close()

        flash(
            "Неверный старый пароль"
        )

        return redirect(
            url_for("cabinet")
        )

    # Проверяем занятость ника
    existing_user = conn.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        AND id != ?
        """,
        (
            new_username,
            session["user_id"]
        )
    ).fetchone()

    if existing_user:

        conn.close()

        flash(
            "Этот ник уже занят"
        )

        return redirect(
            url_for("cabinet")
        )

    conn.execute(
        """
        UPDATE users
        SET username = ?
        WHERE id = ?
        """,
        (
            new_username,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    flash(
        "Ник успешно изменён"
    )

    return redirect(
        url_for("cabinet")
    )


# ==========================================================
# ИЗМЕНЕНИЕ EMAIL
# ==========================================================

@app.route(
    "/change_email",
    methods=["POST"]
)
def change_email():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    new_email = request.form.get(
        "new_email", ""
    ).strip()

    password = request.form.get(
        "email_password", ""
    )

    if not new_email:

        flash(
            "Введите новый email"
        )

        return redirect(
            url_for("cabinet")
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    # Проверяем старый пароль
    if not check_password_hash(
        user["password"],
        password
    ):

        conn.close()

        flash(
            "Неверный старый пароль"
        )

        return redirect(
            url_for("cabinet")
        )

    # Проверяем занятость email
    existing_email = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        AND id != ?
        """,
        (
            new_email,
            session["user_id"]
        )
    ).fetchone()

    if existing_email:

        conn.close()

        flash(
            "Этот email уже занят"
        )

        return redirect(
            url_for("cabinet")
        )

    conn.execute(
        """
        UPDATE users
        SET email = ?
        WHERE id = ?
        """,
        (
            new_email,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    flash(
        "Email успешно изменён"
    )

    return redirect(
        url_for("cabinet")
    )


# ==========================================================
# ИЗМЕНЕНИЕ ПАРОЛЯ
# ==========================================================

@app.route(
    "/change_password",
    methods=["POST"]
)
def change_password():

    if "user_id" not in session:
        return redirect(
            url_for("login")
        )

    old_password = request.form.get(
        "old_password", ""
    )

    new_password = request.form.get(
        "new_password", ""
    )

    new_password2 = request.form.get(
        "new_password2", ""
    )

    # Проверка заполнения
    if not old_password or not new_password or not new_password2:

        flash(
            "Заполните все поля"
        )

        return redirect(
            url_for("cabinet")
        )

    # Проверка новых паролей
    if new_password != new_password2:

        flash(
            "Новые пароли не совпадают"
        )

        return redirect(
            url_for("cabinet")
        )

    # Проверка длины
    if len(new_password) < 6:

        flash(
            "Новый пароль должен содержать минимум 6 символов"
        )

        return redirect(
            url_for("cabinet")
        )

    conn = get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()

    # Проверяем старый пароль
    if not check_password_hash(
        user["password"],
        old_password
    ):

        conn.close()

        flash(
            "Старый пароль введён неправильно"
        )

        return redirect(
            url_for("cabinet")
        )

    # Хешируем новый пароль
    new_password_hash = generate_password_hash(
        new_password
    )

    conn.execute(
        """
        UPDATE users
        SET password = ?
        WHERE id = ?
        """,
        (
            new_password_hash,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    flash(
        "Пароль успешно изменён"
    )

    return redirect(
        url_for("cabinet")
    )


# ==========================================================
# ВЫХОД
# ==========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("index")
    )

# ==========================================================
# РАБОТА / JOB
# ==========================================================

@app.route("/job")
def job():
    return render_template("job.html")


@app.route("/job_apply", methods=["POST"])
def job_apply():

    nickname = request.form.get("nickname", "").strip()
    contact = request.form.get("contact", "").strip()
    mmr = request.form.get("mmr", "").strip()
    role = request.form.get("role", "").strip()
    profile = request.form.get("profile", "").strip()
    about = request.form.get("about", "").strip()

    # Проверяем обязательные поля
    if not nickname or not contact or not mmr or not role:

        flash("Заполните все обязательные поля")

        return redirect(
            url_for("job")
        )

    # Пока заявка просто принимается.
    # Позже сюда можно подключить отправку в Telegram.

    flash(
        "Заявка успешно отправлена!"
    )

    return redirect(
        url_for("job")
    )


# ==========================================================
# О НАС / ABOUT
# ==========================================================

@app.route("/about")
def about():
    return render_template("about.html")


# ==========================================================
# КОНТАКТЫ / CONTACT
# ==========================================================

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ==========================================================
# ЗАПУСК
# ==========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )