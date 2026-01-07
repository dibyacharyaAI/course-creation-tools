from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

Base = declarative_base()

def get_db_engine(database_url: str):
    return create_engine(database_url)

def get_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)
