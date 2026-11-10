from flask import Blueprint, render_template

parser_blueprint = Blueprint("flask_parser", __name__)


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

