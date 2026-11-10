"""Инициализация Flask-приложения.

Создаёт объект :class:`flask.Flask` и настраивает его:

* загружает переменные окружения из ``.env`` (в корне проекта)
  через :func:`dotenv.load_dotenv`;
* берёт ``SECRET_KEY`` из окружения — в коде ключа нет;
* регистрирует blueprint ``parser_blueprint`` внутри
  :func:`create_app`, чтобы разорвать циклическую зависимость:
  ``flask_parser.py`` при импорте сам обращается к ``app``.
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]


def create_app():
    """Собирает и возвращает настроенное Flask-приложение.

    Регистрирует blueprint ``parser_blueprint``, который добавляет
    маршруты ``/`` и ``/index``. Импорт blueprint'а выполняется
    **внутри** функции, а не на уровне модуля, — это разрывает
    циклическую зависимость: ``flask_parser.py`` при импорте
    обращается к ``app`` из этого модуля.

    Note:
        Это «гибридный» паттерн: объект ``app`` уже создан на уровне
        модуля, а фабрика только регистрирует blueprint'ы. Чистая
        фабрика создавала бы ``app = Flask(__name__)`` **внутри**
        функции — тогда можно иметь несколько независимых
        экземпляров приложения (например, для тестов с разными
        конфигами).

    Returns:
        flask.Flask: настроенный объект приложения с
        зарегистрированными blueprint'ами.
    """
    from .flask_parser.flask_parser import parser_blueprint
    from .authorization.auth import auth_blueprint

    app.register_blueprint(parser_blueprint)
    app.register_blueprint(auth_blueprint)
    return app


@app.errorhandler(404)
def not_found(e):
    """Обработчик ошибки 404 («страница не найдена»).

    Рендерит шаблон ``404.html`` вместо стандартной страницы Flask.
    Регистрируется через декоратор
    :meth:`flask.Flask.errorhandler` для кода ``404``.

    Args:
        e: Объект исключения :class:`werkzeug.exceptions.NotFound`,
            переданный Flask автоматически.

    Returns:
        Response: HTML-страница ``404.html``. Код ответа — ``404``
        (Flask выставляет его сам по типу исключения).
    """
    return render_template("404.html")
