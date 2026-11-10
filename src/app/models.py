from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """Модель пользователя для хранения учётных данных.

    Соответствует таблице ``users`` в базе данных. Используется для
    аутентификации и хранения базовой информации о пользователе.

    Attributes:
        id: Уникальный идентификатор пользователя (первичный ключ).
        name: Имя пользователя.
        last_name: Фамилия пользователя.
        email: Адрес электронной почты (не уникален на уровне БД —
            уникальность нужно обеспечить отдельно, если она требуется).
        created: Дата и время создания записи. По умолчанию —
            момент создания объекта (:func:`datetime.now`).
        password: **Хеш** пароля, полученный :func:`hash_password`
            (hex-строка длиной 192 символа: 64 символа соли +
            128 символов хеша). Не пароль в открытом виде. Колонка
            ``VARCHAR(255)`` рассчитана именно на такую длину.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(100))
    created = Column(DateTime(), default=datetime.now)
    password = Column(String(255))

    def __init__(
        self, name=None, last_name=None, email=None, created=None, password=None
    ) -> None:
        """Инициализирует пользователя.

        Все аргументы необязательны, чтобы можно было создать объект
        по частям (например, при частичном обновлении).

        Args:
            name: Имя пользователя.
            last_name: Фамилия пользователя.
            email: Адрес электронной почты.
            created: Дата и время создания. Если не указано, при
                сохранении будет использовано значение по умолчанию
                из колонки (:func:`datetime.now`).
            password: Пароль пользователя.
        """
        self.name = name
        self.last_name = last_name
        self.email = email
        self.created = created
        self.password = password


class Request(Base):
    """Заявка пользователя на подбор вакансий.

    Соответствует таблице ``requests``. Хранит параметры запроса
    (регион, текст запроса, приложенный файл), текущий статус
    обработки и связь с пользователем, создавшим заявку.

    Attributes:
        id: Уникальный идентификатор заявки (первичный ключ).
        user_id: Идентификатор пользователя-владельца заявки
            (внешний ключ на ``users.id``).
        region: Регион поиска вакансий.
        text_request: Текст поискового запроса.
        file_name: Имя приложенного к заявке файла.
        status: Числовой код статуса обработки заявки.
        created: Дата и время создания заявки. По умолчанию —
            момент вставки записи (:func:`datetime.now`).
        updated: Дата и время последнего обновления заявки.
            ``None``, пока заявка ни разу не обновлялась.
        vacancy_number: Количество найденных/обработанных вакансий
            по данной заявке.
        user: Связанный объект :class:``User`` (обратная связь
            доступна через ``User.requests``).
    """

    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    region = Column(String(150))
    text_request = Column(String(150))
    file_name = Column(String(250))
    status = Column(Integer)
    created = Column(DateTime(), default=datetime.now)
    updated = Column(DateTime(), default=None)
    vacancy_number = Column(Integer)
    user = relationship("User", backref="requests")

    def __init__(
        self,
        user_id=None,
        region=None,
        text_request=None,
        file_name=None,
        status=None,
        created=None,
        updated=None,
        vacancy_number=None,
    ) -> None:
        """Инициализирует заявку.

        Все аргументы необязательны: объект можно создать по частям
        и дозаполнить позже. Значения по умолчанию для ``created``
        применяются на уровне колонки при вставке, а не здесь.

        Args:
            user_id: Идентификатор пользователя-владельца заявки.
            region: Регион поиска вакансий.
            text_request: Текст поискового запроса.
            file_name: Имя приложенного файла.
            status: Числовой код статуса обработки.
            created: Дата и время создания. Если ``None``, при
                сохранении подставится :func:`datetime.now`.
            updated: Дата и время последнего обновления. ``None``,
                если заявка ещё не обновлялась.
            vacancy_number: Количество вакансий по заявке.
        """
        self.user_id = user_id
        self.region = region
        self.text_request = text_request
        self.file_name = file_name
        self.status = status
        self.created = created
        self.updated = updated
        self.vacancy_number = vacancy_number
