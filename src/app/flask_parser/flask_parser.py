from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc
from flask_table import Table, Col, LinkCol
import src.parser_app.hhrequest as hr

from ..database import db_session
from ..models import Request

parser_blueprint = Blueprint("flask_parser", __name__)


class Item(object):
    pass


class ItemTable(Table):
    pass


@parser_blueprint.route("/")
def root():
    """Отдаёт корневую страницу приложения.

    Обрабатывает GET-запрос к ``/`` и рендерит шаблон ``index.html``.
    Используется как точка входа для пользователя, открывшего сайт
    по базовому адресу.

    Returns:
        Response: отрендеренный HTML-шаблон ``index.html``.
    """
    return render_template("index.html")


@parser_blueprint.route("/index")
def index():
    """Отдаёт страницу ``/index``.

    Обрабатывает GET-запрос к ``/index`` и рендерит тот же шаблон
    ``index.html``, что и :func:`root`. Существует как явный
    «именованный» URL — на случай, если на страницу нужно ссылаться
    через :func:`flask.url_for` по эндпоинту ``flask_parser.index``,
    а не через корень.

    Returns:
        Response: отрендеренный HTML-шаблон ``index.html``.
    """
    return render_template("index.html")


@parser_blueprint.route("/requests", methods=["GET", "POST"])
def requests():
    """Страница создания заявки на подбор вакансий.

    Доступна только авторизованным пользователям: если в сессии нет
    ``user_id``, происходит редирект на страницу входа.

    GET отдаёт форму ``requests.html``. POST читает поля ``Region``
    и ``Request``, проверяет регион через
    :meth:`HHRequest.set_region` (название должно находиться в
    справочнике hh.ru) и создаёт запись в таблице ``requests``
    со статусом ``0`` («новая заявка»).

    Порядок обработки POST:

    1. Регион проверяется через API hh.ru. При ошибке —
       flash-сообщение и повторный рендер формы.
    2. Создаётся :class:`Request` с ``user_id`` из сессии,
       каноническим названием региона (из ответа API),
       текстом запроса и статусом ``0``.
    3. Запись коммитится. При успехе — flash об отправке; при
       ошибке SQLAlchemy — ``rollback()`` и flash о неудаче.

    Returns:
        Response: редирект на ``login`` для неавторизованных,
        либо отрендеренный ``requests.html`` для GET, успешного
        POST и ошибок валидации региона.
    """
    if session.get("user_id"):
        # Обработка формы по запросу
        if request.method == "POST":
            # Достаем нужные данные из формы запроса
            region = request.form["Region"]
            text_request = request.form["Request"]
            o_hhrequest = hr.HHRequest(None)
            try:
                # Проверяем правильность задания региона
                j_result = o_hhrequest.set_region(region)
            except ValueError:
                flash("Регион указан не правильно")
                return render_template("requests.html")
            # Берем регион из проверки
            region = j_result["items"][0]["text"]
            # Вставляем запрос в БД для обработки
            request_db = Request(
                user_id=session["user_id"],
                region=region,
                text_request=text_request,
                status=0,
            )
            db_session.add(request_db)
            try:
                db_session.commit()
                flash(
                    "Запрос отправлен на обработку."
                    " Его состояние можно отслеживать в истории."
                )
            except SQLAlchemyError:
                db_session.rollback()
                flash("Не удалось сохранить запрос. Попробуйте ещё раз.")
    else:
        # Если пользователь не авторизован то отправляем его в Login
        return redirect("login")
    return render_template("requests.html")


@parser_blueprint.route('/history')
def history():
    """Отдаёт страницу с историей заявок текущего пользователя.

        Доступна только авторизованным: если в сессии нет ``user_id``,
        происходит редирект на страницу входа.

        Для авторизованного пользователя:

        1. Читает из БД список заявок через ``Item.get_element()``.
        2. Оборачивает его в :class:`ItemTable` — HTML-таблицу для
           шаблона.
        3. Рендерит ``history.html``, передавая таблицу в контекст
           под именем ``tables``.

        Returns:
            Response: редирект на ``login`` для неавторизованных,
            либо отрендеренный ``history.html`` с таблицей заявок.
        """
    # Если пользователь не авторизовался, то возвращаем его к странице авторизации
    if session.get("user_id"):
        # Читаем из БД список запросов
        items = Item.get_element()
        # Формируем таблицу
        table = ItemTable(items)
        # Возвращаем страницу с интегрированной таблицей
        return render_template("history.html", tables=table)
    else:
        return redirect("login")
