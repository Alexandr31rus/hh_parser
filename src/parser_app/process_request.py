from sqlalchemy import desc

from ..app.models import Request


def read_requsers(db_session):
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
