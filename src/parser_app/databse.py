import configparser as cfg
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

CONFIG_PATH = Path(__file__).resolve().parent.parent / "app" / "hh_config.ini"
config = cfg.ConfigParser()
if not config.read(CONFIG_PATH):
    raise FileNotFoundError(f"Конфиг не найден: {CONFIG_PATH}")

url = make_url(config["SQLite"]["path"])
if url.database is None:
    raise ValueError(f"В URL БД не указан путь к файлу: {url}")

db_file = Path(url.database).expanduser()
if not db_file.is_absolute():
    db_file = (Path(__file__).resolve().parent / db_file).resolve()
db_file.parent.mkdir(parents=True, exist_ok=True)
url = url.set(database=str(db_file))

engine = create_engine(url)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = Session()
Base = declarative_base()
Base.metadata.create_all(bind=engine)
