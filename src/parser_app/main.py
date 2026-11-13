import sys
import time
import configparser as cfg
from pathlib import Path
from .database import db_session
from .process_request import read_requests, process_request
from sqlalchemy.engine import make_url


def main():
    """Опрашивает БД на новые заявки и обрабатывает их.

    В бесконечном цикле читает через :func:`read_requests` заявки
    со статусом ``0`` («новые»). Логика ветвления:

    * **заявки найдены** — для каждой вызывается
      :func:`process_request`, которая ищет вакансии на hh.ru,
      парсит их и сохраняет результаты;
    * **заявок нет** — пауза 5 секунд, затем в stdout выводится
      счётчик циклов с перезаписью строки через ``\\r`` (без
      засорения терминала).

    Счётчик ``i_cycle`` увеличивается на каждой итерации, независимо
    от того, были ли найдены заявки.
    """
    config_path = Path(__file__).resolve().parent.parent / "app" / "hh_config.ini"
    config = cfg.ConfigParser()
    if not config.read(config_path):
        raise FileNotFoundError(f"Конфиг не найден: {config_path}")

    url = make_url(config["SQLite"]["path"])
    if url.database is None:
        raise ValueError(f"В URL БД не указан путь к файлу: {url}")
    file_folder = Path(config["Json"]["path"]).expanduser()
    if not file_folder.is_absolute():
        file_folder = (Path(__file__).resolve().parent.parent / file_folder).resolve()
    file_folder.mkdir(parents=True, exist_ok=True)
    i_cycle = 0
    while True:
        # Читаем записи со статусом 0 из БД
        rows = read_requests(db_session)
        if rows:
            # Если записи найдены, то начинаем обработку
            for row_request in rows:
                try:
                    process_request(db_session, file_folder, row_request)
                except Exception as e:
                    sys.stderr.write(
                        f'\nОшибка обработки заявки{row_request.id}: {e}\n'
                    )
                    db_session.rollback()
                    continue
        else:
            # Переходим в режим ожидания
            time.sleep(5)
            sys.stdout.write("\r")
            sys.stdout.write(f"Новых запросов не найдено. Цикл {i_cycle}")
            sys.stdout.flush()
        i_cycle += 1
