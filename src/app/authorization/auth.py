from binascii import hexlify
from hashlib import pbkdf2_hmac, sha256
from os import urandom

from flask import Blueprint, flash, redirect, render_template, request

from ..database import db_session
from ..models import User

auth_blueprint = Blueprint("auth", __name__)


def hash_password(password):
    """Хеширует пароль с уникальной солью для безопасного хранения.

    Генерирует случайную соль (60 байт из :func:`os.urandom`, захешированные
    SHA-256) и вычисляет PBKDF2-HMAC-SHA512 от пароля с этой солью и
    100 000 итерациями. Возвращает одну строку «соль + хеш», где оба
    компонента закодированы в hex (ASCII), — её можно сохранять в БД
    как есть.

    Формат результата::

        <64 hex-символа соли><128 hex-символов хеша>

    Соль хранится вместе с хешем, поэтому для проверки пароля её не нужно
    держать отдельно — достаточно взять первые 64 символа сохранённой
    строки. Уникальная соль для каждого пароля исключает атаки по
    радужным таблицам и делает одинаковые пароли разных пользователей
    неотличимыми по хешу.

    Args:
        password: Пароль в открытом виде. Должен быть ``str`` —
            кодируется в UTF-8 внутри функции.

    Returns:
        Строка вида ``"<salt_hex><hash_hex>"`` в ASCII, пригодная для
        хранения в колонке ``VARCHAR`` (минимум 192 символа).
    """
    salt = sha256(urandom(60)).hexdigest().encode("ascii")
    pwdhash = pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 100000)
    pwdhash = hexlify(pwdhash)
    return (salt + pwdhash).decode("ascii")


@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    """Регистрирует нового пользователя.

    GET отдаёт форму ``register.html``. POST читает поля
    ``FirstName``, ``LastName``, ``Email``, ``Password``,
    ``RepeatPassword``, проверяет их и создаёт запись в ``users``.

    Порядок проверок при POST:

    1. Все поля заполнены.
    2. ``Password`` и ``RepeatPassword`` совпадают.
    3. Пользователя с таким ``email`` ещё нет.
    4. Пароль хешируется :func:`hash_password`, объект
       :class:`User` добавляется в сессию и коммитится.

    При успехе — редирект на страницу входа; при занятом email —
    редирект обратно на форму; при несовпадении паролей — форма
    рендерится заново с flash-сообщением.

    Returns:
        Response: редирект на ``auth.login`` при успехе, редирект
        на ``auth.register`` при занятом email, либо отрендеренный
        ``register.html`` для GET и ошибок валидации.

    """
    if request.method == "POST":
        # Достаем из формы данные пользователя
        username = request.form["FirstName"]
        lastname = request.form["LastName"]
        email = request.form["Email"].strip().lower()
        password = request.form["Password"]
        repeat_password = request.form["RepeatPassword"]
        # Проверяем был ли зарегистрирован пользователь с таким же адресом электронной почты
        exists = db_session.query(User).filter(User.email == email).first()

        if not exists:
            # Проверяем пароль
            if password != repeat_password:
                flash("Ошибка при вводе паролей")
                return render_template("register.html")
            else:
                # Хешируем пароль
                h_password = hash_password(password)
                user = User(
                    name=username, last_name=lastname, email=email, password=h_password
                )
                db_session.add(user)
                db_session.commit()
                # Отправляем пользователя на страницу авторизации
                return redirect("login")
        else:
            # Если пользователь с таким же адресом существет, то выдаем ошибку
            flash(
                "Такой пользователь уже зарегистрирован. "
                "Используйте другой адрес электронной почты."
            )
            return redirect("register")
    return render_template("register.html")
