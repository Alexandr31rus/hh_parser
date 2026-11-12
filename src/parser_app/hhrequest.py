import requests as req


class HHRequest:
    """Клиент для работы с API hh.ru.

    Инкапсулирует параметры поиска вакансий (поисковая фраза, регион,
    базовый URL) и постранично собирает ссылки на вакансии. Сами
    вакансии не разбирает — делегирует это объекту-парсеру,
    переданному в конструкторе или через :meth:`set_parser`.

    Типичный сценарий использования::

        client = HHRequest(parser)
        client.set_url("https://api.hh.ru/vacancies?area=#")
        client.set_search_pattern("python")
        client.set_region("Москва")
        for url in client.get_url_vacancies():
            data = client.process_url(url)

    Attributes:
        i_region_id: Идентификатор региона в справочнике hh.ru.
            ``0`` означает, что регион ещё не задан.
    """

    def __init__(self, hhparser) -> None:
        """Инициализирует клиент с пустыми параметрами поиска.

        Args:
            hhparser: Объект-парсер с методом ``parse(data)``, который
                вызывается из :meth:`process_url`. Может быть
                переопределён позже через :meth:`set_parser`.
        """
        self._s_search_pattern = ""
        self._l_ignore_terms = []
        self._l_double_terms = []
        self._s_url = ""
        self._l_urls_vacancies = []
        self._o_parser = hhparser
        self.i_region_id = 0

    def set_search_pattern(self, pattern: str) -> None:
        """Задаёт поисковую фразу для запроса вакансий.

        Args:
            pattern: Текст поискового запроса — то, что передаётся
                в параметре ``text`` API hh.ru.

        Returns:
            None
        """
        self._s_search_pattern = pattern

    def set_url(self, url: str) -> None:
        """Задаёт базовый URL поиска вакансий.

        В URL допускается маркер ``#`` — при вызове
        :meth:`get_url_vacancies` он будет заменён на идентификатор
        региона (:attr:`i_region_id`). Пример::

            https://api.hh.ru/vacancies?area=#

        Args:
            url: Шаблон URL, к которому будут добавляться параметры
                ``text``, ``page``, ``per_page``.

        Returns:
            None
        """
        self._s_url = url

    def set_region(self, name: str) -> dict:
        """Определяет идентификатор региона по его названию.

        Обращается к справочнику регионов hh.ru
        (``/suggests/areas``) и берёт **первое** совпадение — обычно
        это наиболее крупный регион с таким названием (например,
        «Москва» → Москва, а не «Московская область»).

        Args:
            name: Название региона на русском, как его знает hh.ru.

        Returns:
            Словарь ответа API (``dict``) с найденными регионами —
            на случай, если вызывающему коду нужны подробности.

        Raises:
            ValueError: Если по запросу не найдено ни одного региона.
        """
        j_params = {"text": name}
        j_result = req.get("https://api.hh.ru/suggests/areas", params=j_params).json()
        if j_result["items"]:
            self.i_region_id = j_result["items"][0]["id"]
            return j_result
        else:
            raise ValueError("Регион не найден")

    def set_parser(self, hhparser):
        """Заменяет объект-парсер, используемый для разбора вакансий.

        Args:
            hhparser: Объект с методом ``parse(data)`` — например,
                если нужно переключиться на другой формат вывода
                без пересоздания клиента.

        Returns:
            None
        """
        self._o_parser = hhparser

    def get_url_vacancies(self) -> list:
        """Собирает ссылки на все вакансии по заданным параметрам.

        Постранично запрашивает API hh.ru (по 100 вакансий на
        страницу), пока не закончатся результаты или страницы.
        Результат накапливается в ``self._l_urls_vacancies``,
        который очищается в начале каждого вызова.

        Перед запросом проверяет, что заданы URL, поисковая фраза
        и регион. Маркер ``#`` в URL заменяется на
        :attr:`i_region_id`.

        Returns:
            list: Список URL вакансий (строки). Пустой список —
            если API вернул не-200 статус на первой же странице.

        Raises:
            ValueError: Если не задан URL, поисковая фраза или регион.

        Note:
            Цикл останавливается по двум условиям: пустой
            ``items`` в ответе (больше вакансий нет) или
            ``page >= pages - 1`` (достигнута последняя страница).
            Значение ``per_page=100`` — максимум, который отдаёт
            hh.ru за один запрос.

        Note:
            Возвращается **тот же** объект ``self._l_urls_vacancies``,
            а не его копия. Список очищается в начале каждого вызова,
            поэтому предыдущий результат после повторного вызова становится пустым.
        """
        if not self._s_url:
            raise ValueError("Не задан адрес сайта.")

        if not self._s_search_pattern:
            raise ValueError("Не заданы критерии поиска.")

        if self.i_region_id == 0:
            raise ValueError("Не задан регион поиска.")

        url = self._s_url.replace("#", str(self.i_region_id))
        self._l_urls_vacancies.clear()

        i_page_number = 0
        while True:
            j_params = {
                "text": self._s_search_pattern,
                "page": i_page_number,
                "per_page": 100,
            }
            j_result = req.get(url, params=j_params)

            if j_result.status_code != 200:
                return []

            j_result = j_result.json()
            if not j_result["items"]:
                break

            for j_item in j_result["items"]:
                self._l_urls_vacancies.append(j_item["url"])

            if j_result["page"] >= j_result["pages"] - 1:
                break
            else:
                i_page_number += 1
        return self._l_urls_vacancies

    def process_url(self, url: str) -> list:
        """Загружает вакансию по URL и передаёт её парсеру.

        Делает GET-запрос к API, декодирует JSON и вызывает
        ``self._o_parser.parse(data)``. Формат возвращаемого
        значения определяется парсером — метод лишь связывает
        HTTP-запрос и разбор.

        Args:
            url: URL вакансии, обычно из результата
                :meth:`get_url_vacancies`.

        Returns:
            list: То, что вернул ``parse`` парсера. Обычно — список
            строк (например, извлечённые поля вакансии), но тип
            определяется реализацией парсера.
        """
        return self._o_parser.parse(req.get(url).json())
