import re


class HHParserSalary:
    """Парсер зарплаты и грейда из данных вакансии hh.ru.

    Извлекает из словаря вакансии:

    * **грейд** (``Senior`` / ``Middle`` / ``Junior`` / ``Unknown``) —
      по ключевым словам в названии и описании вакансии;
    * **вилку зарплаты** — значения ``from`` и ``to``, приведённые
      к рублям по фиксированным курсам (EUR → 91.92, USD → 82.92,
      остальные валюты — без пересчёта).

    Результат возвращается списком из трёх элементов:
    ``[грейд, зарплата_от, зарплата_до]``.

    Warning:
        Метод :meth:`parse` проверяет, что зарплата вообще указана:
        ``salary`` не ``None`` и хотя бы одна из границ
        (``from``/``to``) не ``None``. Иначе бросается
        :class:`TypeError` с сообщением «Зарплата не указана».
        Случай, когда ``salary`` есть, но обе границы ``None``,
        тоже покрыт.
    """

    def __init__(self):
        """Инициализирует парсер с пустыми значениями.

        Создаёт экземпляр в «пустом» состоянии: список
        ``_l_found_salary`` пуст, тип вакансии — пустая строка.
        Оба атрибута перезаписываются при вызове :meth:`parse`.
        """
        self._l_found_salary = []
        self._s_type_vacancy = ""

    def parse(self, vacancy: dict) -> list:
        """Извлекает грейд и вилку зарплаты из данных вакансии.

        Последовательно:

        1. Определяет грейд по описанию (``description``).
        2. Определяет грейд по названию (``name``) — **перезаписывает**
           результат шага 1.
        3. Приводит валюту к рублям: EUR → ×91.92, USD → ×82.92,
           остальные — без изменений.
        4. Выравнивает вилку: если задана только одна граница —
           вторая приравнивается к ней.

        Args:
            vacancy: Данные вакансии из API hh.ru в виде словаря
                (результат ``requests.Response.json()``).
                Обязательно должен содержать ключи ``description``,
                ``name`` и ``salary`` (последний — словарь с
                ключами ``currency``, ``from``, ``to``).

        Returns:
            list: Список из трёх элементов:
            ``[грейд: str, зарплата_от: float, зарплата_до: float]``.
            Грейд — одна из строк ``"Senior"``, ``"Middle"``,
            ``"Junior"``, ``"Unknown"``. Зарплаты — в рублях
            (для EUR/USD пересчитаны по фиксированному курсу).

        Raises:
            KeyError: Если в ``vacancy`` нет ключей ``description``,
                ``name`` или ``salary``, либо в ``salary`` нет
                ``currency``/``from``/``to``.
            TypeError: Если ``vacancy["salary"]`` равен ``None``
                (зарплата не указана) или если и ``from``, и ``to``
                равны ``None``.

        Note:
            Если ``from`` и ``to`` заданы оба, возвращаются как
            есть (с пересчётом валюты). Если задана только одна
            граница — обе приравниваются к ней, то есть вилка
            превращается в точку.
        """
        self._get_vacancy_type(vacancy["description"])
        self._get_vacancy_type(vacancy["name"])

        salary = vacancy["salary"]
        if salary is None or (salary["from"] is None and salary["to"] is None):
            raise TypeError("Зарплата не указана")

        if vacancy["salary"]["currency"] == "EUR":
            f_coeff = 91.92
        elif vacancy["salary"]["currency"] == "USD":
            f_coeff = 82.92
        else:
            f_coeff = 1.0

        if vacancy["salary"]["from"] is None:
            f_from = vacancy["salary"]["to"]
            f_to = f_from
        elif vacancy["salary"]["to"] is None:
            f_to = vacancy["salary"]["from"]
            f_from = f_to
        else:
            f_from = vacancy["salary"]["from"]
            f_to = vacancy["salary"]["to"]

        return [self._s_type_vacancy, f_from * f_coeff, f_to * f_coeff]

    def _get_vacancy_type(self, vacancy: str):
        """Определяет грейд вакансии по тексту.

        Ищет в переданной строке (приведённой к нижнему регистру)
        ключевые слова грейда и записывает результат в
        ``self._s_type_vacancy``:

        * ``senior`` / ``ведущий`` / ``старший`` → ``"Senior"``;
        * ``junior`` / ``младший`` / ``ученик`` → ``"Junior"``;
        * ``middle`` / ``опытный`` → ``"Middle"``;
        * иначе → ``"Unknown"``.

        Проверки идут **в порядке приоритета**: если в тексте есть
        и ``senior``, и ``junior``, победит ``Senior`` (проверяется
        первым).

        Args:
            vacancy: Текст для анализа — описание или название
                вакансии. Регистр не важен: строка приводится к
                нижнему регистру внутри метода.

        Returns:
            None
        """
        self._l_found_salary = []
        vac_descr: str = vacancy.lower()
        if re.search(r"senior|ведущий|старший", vac_descr):
            self._s_type_vacancy = "Senior"
        elif re.search(r"junior|младший|ученик", vac_descr):
            self._s_type_vacancy = "Junior"
        elif re.search(r"middle|опытный", vac_descr):
            self._s_type_vacancy = "Middle"
        else:
            self._s_type_vacancy = "Unknown"


if __name__ == "__main__":
    pass
