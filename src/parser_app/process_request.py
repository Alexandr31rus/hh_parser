import json
import time
from pathlib import Path

import requests as req
from sqlalchemy import desc

import src.parser_app.hhparser_description as hp
import src.parser_app.hhparser_key_skills as hk
import src.parser_app.hhparser_salary as hs
import src.parser_app.hhrequest as hr

from ..app.models import Request


def read_requests(db_session):
    """Возвращает новые заявки, отсортированные по дате создания.

    Выбирает все записи из ``requests`` со статусом ``0``
    («новая заявка», ещё не обработана) и сортирует их по
    ``created`` по убыванию — самые свежие сверху.

    Args:
        db_session: Активная сессия SQLAlchemy
            (:class:`sqlalchemy.orm.Session`). Передаётся
            явно, чтобы функция не зависела от глобального
            состояния и могла работать в тестах с отдельной
            сессией (например, in-memory SQLite).

    Returns:
        list[Request]: Список ORM-объектов :class:`Request` со
        статусом ``0``, отсортированных по ``created`` по
        убыванию. Пустой список, если таких заявок нет.
    """
    # Выбираем все запросы из БД со статусом 0
    row = (
        db_session.query(Request)
        .filter(Request.status == 0)
        .order_by(desc(Request.created))
        .all()
    )
    return row


def process_request(db_session, file_folder, row_request):
    """Обрабатывает одну заявку: ищет вакансии и сохраняет результат.

    Полный цикл обработки:

    1. Ставит заявке статус ``1`` («в обработке») через
       :func:`update_status`.
    2. Ищет вакансии на hh.ru по региону и тексту запроса из
       ``row_request`` (через :class:`HHRequest`).
    3. Для каждой найденной вакансии (не более 50) запрашивает
       её страницу. **Вакансии с не-200 статусом пропускаются**
       (``continue``) и не учитываются в счётчике.
    4. Для успешно полученных вакансий извлекает технологии из
       описания и ключевых навыков, зарплату и грейд.
    5. Агрегирует результаты: считает частоту технологий,
       усредняет зарплату по грейдам.
    6. Сохраняет итог в JSON-файл в ``file_folder`` (UTF-8).
    7. Обновляет запись в БД: имя файла и количество
       обработанных вакансий через :func:`update_request`.

    Если по запросу ничего не найдено — ставит статус ``2``
    («обработано, вакансий нет») и выходит.

    Args:
        db_session: Активная сессия SQLAlchemy
            (:class:`sqlalchemy.orm.Session`). Используется для
            смены статуса и сохранения результата.
        file_folder: Каталог, в который сохраняется JSON-файл с
            результатами. Должен существовать.
        row_request: ORM-объект :class:`Request` — заявка из БД.
            Обязательные атрибуты: ``user_id``, ``region``,
            ``text_request``.

    Returns:
        None
    """
    # Меняем статус на "В обработке"
    update_status(db_session, row_request, 1)
    # Задаем начальные значения поиска
    s_url = "https://api.hh.ru/vacancies?area=#"

    # Создаем парсеры для извлечения информации
    o_pars_description = hp.HHParserDescription()
    o_pars_salary = hs.HHParserSalary()
    o_pars_key_skills = hk.HHParserKeySkills()

    # Загружаем вспомогательные файлы для парсера описаний вакансий
    o_pars_description.load_help_files("ignore_terms.txt", "double_terms.txt")

    # Создаем класс для работы с парсерами
    o_hhrequest = hr.HHRequest(o_pars_description)
    o_hhrequest.set_url(s_url)

    # Запрашиваем регион поиска у пользователя
    o_hhrequest.set_region(row_request.region)

    # Передаем строку поиска управляющему классу
    o_hhrequest.set_search_pattern(row_request.text_request)

    # Получаем список urls вакансий, удовлетворяющих критерию поиска
    l_urls = o_hhrequest.get_url_vacancies()
    # proxies = {
    #    'http': 'http://65.20.224.102:80'
    # }
    if not l_urls:
        update_status(db_session, row_request, 2)
        print("По Вашему запросу вакансий не найдено")
    else:
        i_number_vacancies = 0
        d_description: dict = {}
        d_key_skills: dict = {}
        d_salary: dict = {
            "Junior": [0, 0, 0],
            "Middle": [0, 0, 0],
            "Senior": [0, 0, 0],
            "Unknown": [0, 0, 0],
        }
        l_salary: list = []
        # Парсим список ссылок на страницы вакансий
        for s_url in l_urls[0:50]:
            # Получаем страницу вакансии
            # , proxies=proxies
            response = req.get(url=s_url)
            if response.status_code != 200:
                continue
            j_vacancy = response.json()
            # Добавляем навыки извлеченные из описания и ключевых навыков
            add_skills(d_description, o_pars_description.parse(j_vacancy))
            add_skills(d_key_skills, o_pars_key_skills.parse(j_vacancy))
            # Обрабатываем зарплату
            l_salary = o_pars_salary.parse(j_vacancy)
            if l_salary:
                process_salary(d_salary, l_salary)
            i_number_vacancies += 1

        # Сортируем навыки по частоте упоминаний
        d_skills_sorted = sort_skills(d_key_skills, i_number_vacancies)
        d_skills_description_sorted = sort_skills(d_description, i_number_vacancies)
        # Усредняем зарплату
        d_salary = avg_salary(d_salary)

        # Формируем словарь с навыками и зарплатой
        d_sum: dict = {
            "salary": d_salary,
            "description": d_skills_description_sorted,
            "keyskills": d_skills_sorted,
        }

        # Записываем словарь в формате json в файл, в указанный каталог
        # file_name: str = (
        #     file_folder
        #     + "/"
        #     + str(row_request.user_id)
        #     + "-"
        #     + "".join(row_request.text_request)
        #     + "-"
        #     + row_request.region
        #     + "-"
        #     + time.strftime("%Y%m%d%H%M", time.localtime())
        # )
        file_name = Path(file_folder) / (
            f"{row_request.user_id}"
            f"-{row_request.text_request}"
            f"-{row_request.region}"
            f"-{time.strftime('%Y%m%d%H%M', time.localtime())}.json"
        )
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(d_sum, f)
        # Обновляем запись с результатами запроса
        update_request(db_session, row_request, file_name, i_number_vacancies)


def update_status(db_session, row_request, status):
    pass


def update_request(db_session, row_request, file_name, number_vacancies):
    pass


def add_skills(sum_skills: dict, skills_to_add: list):
    """Добавляет технологии в словарь с подсчётом частоты.

        Для каждого элемента ``skills_to_add`` увеличивает счётчик в
        ``sum_skills``: если технология уже есть — ``+1``, если нет —
        создаёт запись со значением ``1``. Словарь **мутируется** —
        изменения видны вызывающему коду.

        Args:
            sum_skills: Словарь-аккумулятор вида
                ``{технология: count}``. Мутируется.
            skills_to_add: Список технологий, которые нужно добавить
                (результат :meth:`HHParserDescription.parse` или
                :meth:`HHParserKeySkills.parser`). Повторы **не
                отсеиваются**: если технология встречается в списке
                несколько раз, счётчик увеличится на каждый.

        Returns:
            None
        """
    for s_skill in skills_to_add:
        if s_skill in sum_skills:
            sum_skills[s_skill] += 1
        else:
            sum_skills[s_skill] = 1


def sort_skills(skills: dict, vacancies_number: int) -> dict:
    """Сортирует технологии по частоте и переводит счётчики в проценты.

        Сортирует словарь ``{технология: count}`` по убыванию ``count``
        (самые частые сверху), затем заменяет каждое значение на долю
        в процентах от ``vacancies_number``, округлённую до двух знаков
        после запятой.

        Args:
            skills: Словарь вида ``{технология: count}`` — результат
                накопления через :func:`add_skills`.
            vacancies_number: Общее число обработанных вакансий.
                Используется как делитель: ``count / vacancies_number
                * 100``. **Не должен быть нулём** — иначе
                :class:`ZeroDivisionError`.

        Returns:
            dict: Новый словарь ``{технология: процент}``, где
            ``процент`` — ``float`` с двумя знаками после запятой.
            Порядок ключей сохраняет сортировку по убыванию частоты
            (Python 3.7+ гарантирует порядок вставки в ``dict``).
        """
    if vacancies_number == 0:
        return {}
    d_sorted: dict = dict(sorted(skills.items(), key=lambda x: x[1], reverse=True))
    for key, value in d_sorted.items():
        d_sorted[key] = round((value / vacancies_number) * 100, 2)
    return d_sorted


def process_salary(all_salary: dict, salary: list) -> dict:
    return {}


def avg_salary(all_salary: dict) -> dict:
    return {}
