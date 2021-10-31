"""
Base class for Notebook entity and its realisations
for mongo and Postgres DataBases
"""

# pylint: disable=W0614
# pylint: disable=R0903
# pylint: disable=W0703
# pylint: disable=W0401
# pylint: disable=E0402
# pylint: disable=R0801

from datetime import datetime
from datetime import date
import re
import sys
import os
from abc import ABC, abstractmethod
from sqlalchemy import or_, update, delete


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
if __package__ == "" or __package__ is None:
    from SQL_alchemy_classes import *
    from LRU_cache import *
else:
    from .SQL_alchemy_classes import *
    from .LRU_cache import *


class Notebook(ABC):
    """
    Base class fore Notebook entity
    """

    @abstractmethod
    def __init__(self):
        """
        Abstract method
        """

    @abstractmethod
    def get_all_notes(self):
        """
        Abstract method
        """

    @abstractmethod
    def get_notes(self, keyword):
        """
        Abstract method
        """

    @abstractmethod
    def get_note_by_id(self, note_id):
        """
        Abstract method
        """

    @abstractmethod
    def update_note(self, note_id, keywords, text):
        """
        Abstract method
        """

    @abstractmethod
    def insert_note(self, keywords, text):
        """
        Abstract method
        """

    @abstractmethod
    def delete_note(self, note_id):
        """
        Abstract method
        """


class NotebookMongo(Notebook):
    """
    Class Notebook that operates with Mongo
    """

    def __init__(self, notes_db, counter_db):
        super().__init__()
        self.notes = []
        self.notes_db = notes_db
        self.counter_db = counter_db

    @LRU_cache(1)
    def get_all_notes(self):
        """
        Get all the Notes from Mongo collection
        :return: list of NoteMongo
        """
        self.notes = []
        try:
            result = self.notes_db.find({}).sort("note_id")
            for res in result:
                self.notes.append(NoteMongo(res))
            return self.notes
        except Exception as error:
            return str(error)

    @LRU_cache(10)
    def get_notes(self, keyword):
        """
        Get Notes from Mongo collection find by keywords in fields text, keywords
        :param keyword: str
        :return: list of NoteMongo
        """
        self.notes = []
        try:
            if keyword != "":
                rgx = re.compile(f".*{keyword}.*", re.IGNORECASE)
                result = self.notes_db.find(
                    {"$or": [{"keywords": rgx}, {"text": rgx}]}
                ).sort("note_id")
                for res in result:
                    self.notes.append(NoteMongo(res))
            return self.notes
        except Exception as error:
            return str(error)

    @LRU_cache(10)
    def get_note_by_id(self, note_id):
        """
        Get  Note from Mongo collection by note_id
        :param note_id: str/int
        :return: NoteMongo
        """
        try:
            result = self.notes_db.find_one({"note_id": int(note_id)})
            if result is not None:
                return NoteMongo(result)
            return None
        except Exception as error:
            return str(error)

    @LRU_cache_invalidate("get_notes", "get_all_notes", "get_note_by_id")
    def update_note(self, note_id, keywords, text):
        """
        Update Note selected by note_id with new text and keywords
        :param note_id:
        :param keywords:
        :param text:
        :return: 0 if OK or error otherwise
        """
        try:
            if "," in keywords:
                keywords = [k.strip() for k in keywords.split(",")]
            elif " " in keywords:
                keywords = [k.strip() for k in keywords.split(" ")]
            else:
                keywords = [keywords]
            self.notes_db.replace_one(
                {"note_id": int(note_id)},
                {
                    "note_id": int(note_id),
                    "created_at": datetime.today(),
                    "keywords": keywords,
                    "text": text,
                },
            )
            return 0
        except Exception as error:
            return error

    @LRU_cache_invalidate("get_notes", "get_all_notes")
    def insert_note(self, keywords, text):
        """
        Insert new note to DB
        :param keywords: str
        :param text: str
        :return: 0 if OK or error otherwise
        """
        try:
            counter = self.counter_db.find_one(
                {"counter_name": "note_id"}, {"value": 1}
            )["value"]
            self.counter_db.replace_one(
                {"counter_name": "note_id"},
                {"counter_name": "note_id", "value": counter + 1},
            )
            if "," in keywords:
                keywords = [k.strip() for k in keywords.split(",")]
            elif " " in keywords:
                keywords = [k.strip() for k in keywords.split(" ")]
            else:
                keywords = [
                    keywords,
                ]
            self.notes_db.insert_one(
                {
                    "note_id": (counter + 1),
                    "keywords": keywords,
                    "text": text,
                    "created_at": datetime.today(),
                }
            )
            return 0
        except Exception as error:
            return error

    @LRU_cache_invalidate("get_notes", "get_all_notes", "get_note_by_id")
    def delete_note(self, note_id):
        """
        Delete note selected by note_id
        :param note_id: int
        :return: 0 if OK or error otherwise
        """
        try:
            self.notes_db.delete_one({"note_id": int(note_id)})
            return 0
        except Exception as error:
            return error


class NotebookPSQL(Notebook):
    """
    Class Notebook that operates with Postgres
    """

    def __init__(self, session=None):
        super().__init__()
        self.session = session
        self.notes = []

    @LRU_cache(1)
    def get_all_notes(self):
        """
        Find all the notes in DB
        :return: list of NotePSQL
        """
        self.notes = []
        result = (
            self.session.query(
                Note_.note_id, Note_.keywords, Text.text, Note_.created_at
            )
            .join(Text)
            .order_by(Note_.note_id)
            .all()
        )
        for res in result:
            self.notes.append(NotePSQL(res))
        return self.notes

    @LRU_cache(10)
    def get_notes(self, keyword):
        """
        Select from DB Notes find by keyword for fields text, keywords
        :param keyword: str
        :return: list of NotePSQL
        """
        self.notes = []
        if keyword != "":
            result = (
                self.session.query(
                    Note_.note_id, Note_.keywords, Text.text, Note_.created_at
                )
                .join(Text)
                .filter(
                    or_(
                        func.lower(Note_.keywords).like(func.lower(f"%{keyword}%")),
                        func.lower(Text.text).like(func.lower(f"%{keyword}%")),
                    )
                )
                .order_by(Note_.note_id)
                .all()
            )
            for res in result:
                self.notes.append(NotePSQL(res))
            return self.notes
        return []

    @LRU_cache(10)
    def get_note_by_id(self, note_id):
        """
        Select from DB Note by given note_id
        :param note_id: int
        :return: NotePSQL
        """
        result = (
            self.session.query(
                Note_.note_id, Note_.keywords, Text.text, Note_.created_at
            )
            .join(Text)
            .filter(Note_.note_id == note_id)
            .first()
        )
        if result:
            return NotePSQL(result)
        return None

    @LRU_cache_invalidate("get_notes", "get_all_notes", "get_note_by_id")
    def update_note(self, note_id, keywords, text):
        """
        Update Note selected by note_id with new keywords and text
        :param note_id: int
        :param keywords: str
        :param text: str
        :return: 0 if OK or error otherwise
        """
        try:
            if "," in keywords:
                keywords = [k.strip() for k in keywords.split(",")]
            elif " " in keywords:
                keywords = [k.strip() for k in keywords.split(" ")]
            else:
                keywords = [
                    keywords,
                ]
            self.session.execute(
                update(Note_, values={Note_.keywords: ",".join(keywords)}).filter(
                    Note_.note_id == note_id
                )
            )
            self.session.execute(
                update(Text, values={Text.text: text}).filter(Text.note_id == note_id)
            )
            self.session.commit()
            return 0
        except Exception as error:
            self.session.rollback()
            return error

    @LRU_cache_invalidate("get_notes", "get_all_notes")
    def insert_note(self, keywords, text):
        """
        Insert new Note to DB
        :param keywords: str
        :param text: str
        :return: 0 if OK or error otherwise
        """
        try:
            if "," in keywords:
                keywords = [k.strip() for k in keywords.split(",")]
            elif " " in keywords:
                keywords = [k.strip() for k in keywords.split(" ")]
            else:
                keywords = [
                    keywords,
                ]

            note = Note_(keywords=",".join(keywords), created_at=date.today())
            self.session.add(note)
            self.session.commit()
            text = Text(note_id=note.note_id, text=text)
            self.session.add(text)
            self.session.commit()
            return 0
        except Exception as error:
            self.session.rollback()
            return error

    @LRU_cache_invalidate("get_notes", "get_all_notes", "get_note_by_id")
    def delete_note(self, note_id):
        """
        Delete Note from DB by note_id
        :param note_id: int
        :return: 0 if OK or exception otherwise
        """
        sql_stmt = delete(Note_).where(Note_.note_id == note_id)
        return run_sql(self.session, sql_stmt)

class NoteAbstract(ABC):
    """
    Abstract Note class
    """

    @abstractmethod
    def __init__(self):
        self.note_id = None
        self.keywords = None
        self.created_at = None
        self.text = None


class NoteMongo(NoteAbstract):
    """
    Class Notes initialized from Mongo cursor
    """

    def __init__(self, json):
        super().__init__()
        self.note_id = json["note_id"]
        self.keywords = ",".join(json["keywords"])
        self.created_at = json["created_at"]
        self.text = json["text"]


class NotePSQL(NoteAbstract):
    """
    Class Notes initialized from SQLAlchemy query
    """

    def __init__(self, note):
        super().__init__()
        self.note_id = note.note_id
        self.created_at = note.created_at
        self.keywords = note.keywords
        self.text = note.text
