import re


class HHParserDescription:
    """Парсер описания вакансии для извлечения технологий.

    Принимает словарь с данными вакансии из API hh.ru, берёт поле
    ``description`` и прогоняет его через цепочку очисток, после
    чего выделяет упоминания технологий:

    1. :meth:`_clean_trash` — удаляет пунктуацию и мусорные символы.
    2. :meth:`_clean_html` — убирает HTML-разметку.
    3. :meth:`_find_technology` — оставляет слова, похожие на
       названия технологий (латиница, с заглавной буквы), собирает
       двойные термины, вычитает игнорируемые и убирает повторы.

    Вспомогательные списки ``_l_ignore_terms`` и ``_l_double_terms``
    заполняются через :meth:`load_help_files` и влияют на результат
    :meth:`_find_technology`.
    """

    def __init__(self):
        """Инициализирует парсер с пустыми списками и описанием.

        Создаёт экземпляр в «пустом» состоянии: списки найденных
        технологий, игнорируемых и двойных терминов пусты,
        ``_s_description`` — пустая строка. Вспомогательные списки
        заполняются позже через :meth:`load_help_files`, а описание —
        при вызове :meth:`parse`.
        """
        self._l_found_technology = []
        self._s_description = ""
        self._l_ignore_terms = []
        self._l_double_terms = []

    def parse(self, vacancy: dict):
        """Извлекает технологии из описания вакансии.

        Принимает словарь с данными вакансии из API hh.ru, берёт
        поле ``description`` и последовательно прогоняет его через
        :meth:`_clean_trash`, :meth:`_clean_html` и
        :meth:`_find_technology`. Результат сохраняется в
        ``self._l_found_technology``.

        Args:
            vacancy: Данные вакансии из API hh.ru в виде словаря
                (результат ``requests.Response.json()``).
                Обязательно должен содержать ключ ``description``
                с текстом описания вакансии.

        Returns:
            list: Список найденных технологий — **тот же объект**,
            что лежит в ``self._l_found_technology``, а не копия.
            При следующем вызове :meth:`parse` он будет
            перезаписан.

        Raises:
            KeyError: Если в ``vacancy`` нет ключа ``description``
                — например, API вернул ответ с ошибкой вместо
                вакансии.
        """
        self._s_description = vacancy["description"]
        self._clean_trash()
        self._clean_html()
        self._find_technology()
        return self._l_found_technology

    def _clean_trash(self):
        """Удаляет из описания пунктуацию и мусорные символы.

        Последовательно убирает запятые, точки с запятой, скобки,
        кавычки-ёлочки и восклицательные знаки. Дополнительно
        применяет регулярное выражение для очистки от символов,
        не являющихся буквами английского алфавита.

        Returns:
            None
        """
        re_cleaner = re.compile("['^A-Za-z0-9]+")
        self._s_description = re_cleaner.sub(" ", self._s_description)
        self._s_description = self._s_description.replace(",", "")
        self._s_description = self._s_description.replace(";", "")
        self._s_description = self._s_description.replace(")", "")
        self._s_description = self._s_description.replace("(", "")
        self._s_description = self._s_description.replace("«", "")
        self._s_description = self._s_description.replace("»", "")
        self._s_description = self._s_description.replace("!", "")

    def _clean_html(self) -> None:
        """Удаляет из описания HTML-теги.

        Заменяет все подстроки вида ``<...>`` на пустую строку.
        Регулярное выражение не жадное (``.*?``), поэтому
        последовательные теги обрабатываются по одному.

        Returns:
            None
        """
        re_cleaner = re.compile("<.*?>")
        self._s_description = re.sub(re_cleaner, "", self._s_description)

    def _find_technology(self) -> None:
        """Выделяет технологии из очищенного описания.

        Работает с ``self._s_description`` (уже прогнанным через
        :meth:`_clean_trash` и :meth:`_clean_html`) и заполняет
        ``self._l_found_technology``. Этапы:

        1. Разбивает описание на слова, отбрасывает те, что
           начинаются с кириллицы.
        2. Оставляет слова с заглавной первой буквы (``istitle``).
        3. Собирает двойные термины через
           :meth:`_process_double_terms`.
        4. Убирает игнорируемые через :meth:`_clean_ignore_terms`.
        5. Убирает повторы через ``set``.

        Returns:
            None
        """
        # Убираем русский текст
        l_tech = self._s_description.split()
        self._l_found_technology = [
            word for word in l_tech if not re.match("[А-Яа-я]", word)
        ]
        # Убираем слова, которые не начинаются с большой буквы
        self._l_found_technology = [
            word for word in self._l_found_technology if word.istitle()
        ]
        # Собираем термины, состоящие из двух слов
        self._l_found_technology = self._process_double_terms(self._l_found_technology)
        # Убираем слова, присутствующие в файле ignore
        self._l_found_technology = self._clean_ignore_terms(self._l_found_technology)
        # Убираем повторы
        self._l_found_technology = list(set(self._l_found_technology))

    def _clean_ignore_terms(self, terms: list) -> list:
        """Удаляет из списка терминов игнорируемые слова.

        Вычитает из ``terms`` содержимое ``self._l_ignore_terms``.
        Сравнение — точное совпадение строк (регистрозависимое).

        Args:
            terms: Список терминов-кандидатов.

        Returns:
            list: Новый список без игнорируемых слов. Если
            ``self._l_ignore_terms`` пуст — возвращается **копия**
            исходного списка (сам ``terms`` не мутируется).
        """
        # Если список мусорных слов пуст, то возвращаем изначальный список слов
        if not self._l_ignore_terms:
            return terms

        # Очищаем список от мусорных слов
        l_result = terms.copy()
        l_result = [term for term in l_result if term not in self._l_ignore_terms]
        return l_result

    def _process_double_terms(self, terms: list) -> list:
        """Склеивает двойные термины и убирает их из одиночных.

        Ищет в объединённой строке из ``terms`` каждую фразу из
        ``self._l_double_terms``. Найденные фразы вырезаются из
        строки целиком (чтобы их слова не попали в результат
        по отдельности) и добавляются в результат как единый
        элемент.

        Args:
            terms: Список одиночных терминов.

        Returns:
            list: Список, в котором двойные термины представлены
            едиными строками, а их составляющие удалены. Если
            ``self._l_double_terms`` пуст — возвращается исходный
            ``terms`` (тот же объект, не копия).

        """
        # Если список с терминами из двух слов пуст,
        # то возвращаем начальный список
        if not self._l_double_terms:
            return terms

        # Преобразуем список с учетом двойных терминов
        l_result_double = []
        s_result = " ".join(terms)
        for double_term in self._l_double_terms:
            if double_term in s_result:
                l_result_double.append(double_term)
                s_result = s_result.replace(double_term, " ")
        l_result = s_result.split(" ")
        l_result.extend(l_result_double)
        return l_result

    def load_help_files(self, file_ignore: str, file_double: str) -> None:
        """Загружает вспомогательные файлы с терминами.

        Читает два файла построчно и заполняет списки:

        * ``file_ignore`` → ``self._l_ignore_terms`` — слова,
          которые нужно исключать из результата;
        * ``file_double`` → ``self._l_double_terms`` — фразы из
          двух слов, которые нужно склеивать в один термин.

        Файлы открываются в UTF-8, строки очищаются через
        ``strip()`` (убирает ``\\n``, ``\\r`` и пробелы по
        краям).

        Args:
            file_ignore: Путь к файлу с игнорируемыми терминами
                (по одному на строку).
            file_double: Путь к файлу с двойными терминами
                (по одной фразе на строку).

        Returns:
            None
        """
        # Открываем файл с терминами, которые надо игнорировать
        try:
            with open(file_ignore, "r", encoding="utf-8") as f:
                for ignore_term in f:
                    self._l_ignore_terms.append(ignore_term.strip())
        except FileNotFoundError:
            self._l_ignore_terms = []
        # Открываем файл с терминами, состоящими из двух слов
        try:
            with open(file_double, "r", encoding="utf-8") as f:
                for double_term in f:
                    self._l_double_terms.append(double_term.strip())
        except FileNotFoundError:
            self._l_double_terms = []


if __name__ == "__main__":
    pass
