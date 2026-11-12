class HHParserKeySkills:
    """Парсер ключевых навыков из данных вакансии hh.ru.

    Берёт из словаря вакансии поле ``key_skills`` — список словарей
    вида ``[{"name": "Python"}, {"name": "SQL"}, ...]`` — и
    извлекает из него названия технологий.

    Результат возвращается в виде списка уникальных названий
    (без повторов, порядок не гарантирован).
    """

    def __init__(self):
        """Инициализирует парсер с пустым списком найденных технологий.

        Создаёт экземпляр в «пустом» состоянии: ``_l_found_technology``
        — пустой список. Атрибут ``_l_skills`` здесь **не задаётся** —
        он появляется только при вызове :meth:`parser`.
        """
        self._l_found_technology = []

    def parse(self, vacancy: dict) -> list:
        """Извлекает ключевые навыки из данных вакансии.

        Сбрасывает предыдущий результат, читает поле ``key_skills``
        из ``vacancy`` и, если оно непустое, заполняет
        ``_l_found_technology`` названиями технологий через
        :meth:`_find_technology`.

        Args:
            vacancy: Данные вакансии из API hh.ru в виде словаря
                (результат ``requests.Response.json()``).
                Обязательно должен содержать ключ ``key_skills`` —
                список словарей с ключом ``name``.

        Returns:
            list: Список уникальных названий технологий. Пустой
            список, если ``key_skills`` пуст (``[]`` или ``None``).
            Порядок не гарантирован — результат строится через
            ``set``.

        Raises:
            KeyError: Если в ``vacancy`` нет ключа ``key_skills``
                или в каком-то из элементов нет ключа ``name``.
        """
        self._l_found_technology = []
        self._l_skills = vacancy["key_skills"]
        if self._l_skills:
            self._find_technology()
        else:
            self._l_found_technology = []
        return list(set(self._l_found_technology))

    def _find_technology(self) -> None:
        """Собирает названия технологий из ``self._l_skills``.

        Проходит по списку словарей ``self._l_skills`` (каждый —
        вида ``{"name": "Python", ...}``) и добавляет значение
        ``["name"]`` в ``self._l_found_technology``. Повторы не
        отсеиваются на этом этапе — это делает вызывающий
        :meth:`parser` через ``set``.

        Returns:
            None
        """
        for tec_dic in self._l_skills:
            self._l_found_technology.append(tec_dic["name"])


if __name__ == "__main__":
    pass
