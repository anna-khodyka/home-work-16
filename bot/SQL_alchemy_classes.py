"""
Define SQLAlchemy ORM classes for Contact-book and Notebook entities
"""

# pylint: disable=R0903
# pylint: disable=C0103
# pylint: disable=W0703

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    func,
    UniqueConstraint,
    Date,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Contact(Base):
    """
    Table Contact stored base data for contact.
    Other data stored in joined tables Email_, Phones_, Address_

    """

    __tablename__ = "contact"
    contact_id = Column(
        Integer,
        primary_key=True,
    )
    name = Column(String(50), nullable=False)
    created_at = Column(Date, server_default=func.now(), nullable=False)
    birthday = Column(Date, nullable=True)
    __table_args__ = (UniqueConstraint("name", "birthday", name="uc_1"),)


class Phone_(Base):
    """
    Table Phone_ stored phones for contacts in table Contact
    """

    __tablename__ = "phone"
    phone_id = Column(
        Integer,
        primary_key=True,
    )
    phone = Column(String(15), nullable=True)
    contact_id = Column(
        Integer,
        ForeignKey("contact.contact_id", onupdate="CASCADE", ondelete="CASCADE"),
    )
    contact = relationship("Contact")
    __table_args__ = (UniqueConstraint("phone", name="up_1"),)


class Email_(Base):
    """
    Table Email_ stored email addresses for contacts in table Contact
    """

    __tablename__ = "email"
    email_id = Column(
        Integer,
        primary_key=True,
    )
    email = Column(String(50), nullable=True)
    contact_id = Column(
        Integer,
        ForeignKey("contact.contact_id", onupdate="CASCADE", ondelete="CASCADE"),
    )
    contact = relationship("Contact")
    __table_args__ = (UniqueConstraint("email", name="ue_1"),)


class Address_(Base):
    """
    Table Address_ stored addresses for contacts in table Contact
    """

    __tablename__ = "address"
    address_id = Column(
        Integer,
        primary_key=True,
    )
    zip = Column(String(10), default="")
    country = Column(String(50), default="")
    region = Column(String(50), default="")
    city = Column(String(40), default="")
    street = Column(String(50), default="")
    house = Column(String(5), default="")
    apartment = Column(String(5), default="")
    contact_id = Column(
        Integer,
        ForeignKey("contact.contact_id", onupdate="CASCADE", ondelete="CASCADE"),
    )
    contact = relationship("Contact")


class Note_(Base):
    """
    Table Note_
    """

    __tablename__ = "note"
    note_id = Column(
        Integer,
        primary_key=True,
    )
    keywords = Column(String(250))
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class Text(Base):
    """
    Table Text stored texts for Note_ Table
    """

    __tablename__ = "text"
    text_id = Column(
        Integer,
        primary_key=True,
    )
    text = Column(String(500))
    note_id = Column(
        Integer, ForeignKey("note.note_id", onupdate="CASCADE", ondelete="CASCADE")
    )
    note = relationship("Note_")


class User_(Base):
    """
    Table for Flask user
    """

    __tablename__ = "user_"
    id = Column(
        Integer,
        primary_key=True,
    )
    username = Column(String(50))
    login = Column(String(50))
    password = Column(String(150))
    __table_args__ = (UniqueConstraint("login", name="ul_1"),)

def run_sql(session, sql_stmt):
    """
    Do wide shared in classes SQL session routine
    :param session: pgdb session
    :param sql_stmt: str
    :return: o or error
    """
    try:
        session.execute(sql_stmt)
        session.commit()
        return 0
    except Exception as error:
        session.rollback()
        return error
