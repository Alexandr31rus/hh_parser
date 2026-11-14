from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc
from flask_table import Table, Col, LinkCol
import src.parser_app.hhrequest as hr

from ..database import db_session
from ..models import Request

parser_blueprint = Blueprint("flask_parser", __name__)


class Item(object):
    """Запись истории заявок — строка для таблицы на странице ``/history``.

        Обёртка над :class:`Request` с «человеческими» значениями:

        * ``tab_id`` — порядковый номер для отображения (1, 2, 3, …);
        * ``request_id`` — реальный ``id`` заявки в БД (для ссылок,
          действий);
        * ``status`` — текстовое описание статуса
          (``Инициализирован`` / ``В обработке`` / ``Завершен`` /
          ``Неопределен``) вместо числового кода;
        * ``vacancies_number`` — число вакансий, где ``None`` заменён
          на ``0``.

        Экземпляры создаются только через :meth:`get_element` (или
        :meth:`get_element_by_id`) — напрямую из модели ``Request``.
    """

    def __init__(self, tab_id, req_id, region, text_request, status, vac_number, created):
        """Создаёт запись истории заявки.

        Args:
            tab_id: Порядковый номер для отображения в таблице
                (1, 2, 3, …). Не совпадает с ``request_id`` —
                это просто нумерация строк.
            req_id: Реальный ``id`` заявки из таблицы ``requests``.
            region: Название региона поиска.
            text_request: Текст поискового запроса.
            status: Текстовое описание статуса
                (``Инициализирован`` / ``В обработке`` /
                ``Завершен`` / ``Неопределен``).
            vac_number: Количество найденных вакансий. ``0``,
                если заявка ещё не обработана.
            created: Дата и время создания заявки
                (:class:`datetime.datetime`).
        """
        self.tab_id = tab_id
        self.request_id = req_id
        self.region = region
        self.text_request = text_request
        self.vacancies_number = vac_number
        self.status = status
        self.created = created

    @classmethod
    def get_element(cls):
        """Возвращает историю заявок текущего пользователя.

        Читает из БД все заявки пользователя из ``session["user_id"]``,
        отсортированные по ``created`` по убыванию (свежие сверху),
        и преобразует их в список :class:`Item` для отображения:

        * числовой статус (``0``/``1``/``2``) заменяется на
          текстовый (``Инициализирован`` / ``В обработке`` /
          ``Завершен`` / ``Неопределен``);
        * ``vacancy_number = None`` заменяется на ``0``;
        * каждому элементу присваивается порядковый ``tab_id``
          (1, 2, 3, …).

        Returns:
            list[Item]: Список записей истории, отсортированный по
            дате создания (свежие сверху). Пустой список, если у
            пользователя нет заявок.
        """
        # Читаем из БД список запросов для текущего пользователя
        rows = db_session.query(Request).filter(Request.user_id == session["user_id"]).order_by(
            desc(Request.created)).all()
        id_n = 1
        items_for_table = []
        # Обрабатываем полученный список
        for row_request in rows:
            # Вместо None устанавливаем количество вакансий в 0
            vac_number = row_request.vacancies_number
            if not row_request.vacancies_number:
                vac_number = 0
            # Обрабатываем статус запроса
            if row_request.status == 0:
                status = 'Инициализирован'
            elif row_request.status == 1:
                status = 'В обработке'
            elif row_request.status == 2:
                status = 'Завершен'
            else:
                status = 'Неопределен'
            # Добавляем элемент в таблицу
            items_for_table.append(
                Item(id_n, row_request.id, row_request.region, row_request.text_request, status, vac_number,
                     row_request.created))
            id_n += 1
        return items_for_table

    @classmethod
    def get_element_by_id(cls, id):
        """Возвращает запись истории по её порядковому номеру ``tab_id``.

        Ищет в результате :meth:`get_element` элемент с
        ``tab_id == id`` и возвращает его.

        Args:
            id: Порядковый номер строки в таблице (``tab_id``,
                начиная с 1), а не ``id`` заявки в БД. Для поиска
                по реальному ``id`` используйте атрибут
                ``request_id``.

        Returns:
            Item: Запись истории с указанным ``tab_id``.
        """
        return [i for i in cls.get_element() if i.tab_id == id][0]


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
