"""Точка входа для локального запуска Flask-приложения.

Запускает два процесса параллельно:

* **Flask-сервер** (development) на ``http://127.0.0.1:5000`` —
  без ``debug=True``, чтобы не включать reloader;
* **фоновый парсер** hh.ru — отдельный процесс
  :class:`multiprocessing.Process` с именем ``HH API Parser``,
  который крутит :func:`parser_app.main.main` (опрос БД на новые
  заявки).

Запуск::

    python -m src.app.main
"""

import multiprocessing as mp

from src.app import create_app
from src.parser_app import main as pr

if __name__ == "__main__":
    # create_app() собирает приложение: регистрирует blueprint'ы,
    # подгружает конфиг. Вызывается только при прямом запуске файла,
    # чтобы импорт модуля (например, из тестов) не поднимал сервер.
    app = create_app()

    par_service = mp.Process(name="HH API Parser", target=pr.main)
    par_service.start()
    # Запуск Flask приложения
    try:
        app.run()
    finally:
        # Flask не возвращает управление до Ctrl+C, поэтому
        # остановка парсера — именно в finally. Иначе при
        # KeyboardInterrupt дочерний процесс останется «сиротой»
        # и продолжит писать в БД.
        par_service.terminate()
        par_service.join()
