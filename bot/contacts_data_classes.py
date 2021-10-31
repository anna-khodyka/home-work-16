# pylint: disable=R0903
# pylint: disable=C0412
# pylint: disable=R0902
# pylint: disable=W0703
# pylint: disable=R0201
# pylint: disable=E0402
# pylint: disable=E0602
# pylint: disable=W0401

"""
Classes that provides interaction between views and database for
contact book entities. Includes Mongo and Postgres interface.
Redis based LRU cache used
"""

import re
import sys
import os
from datetime import date
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from sqlalchemy import or_, update, delete, any_, func


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

if __package__ == "" or __package__ is None:
    from SQL_alchemy_classes import (
        Address_,
        Contact,
        Email_,
        Phone_,
        run_sql
    )
    from LRU_cache import LRU_cache, LRU_cache_invalidate
else:
    from .SQL_alchemy_classes import *
    from .LRU_cache import *


class Contactbook(ABC):
    """
    Abstract class for Contactbook
    """

    @abstractmethod
    def __init__(self):
        """
        Abstract method
        """

    @abstractmethod
    def get_all_contacts(self):
        """
        Abstract method
        """

    @abstractmethod
    def get_contacts(self, key):
        """
        Abstract method
        """

    @abstractmethod
    def get_contact_details(self, contact_id):
        """
        Abstract method
        """

    @abstractmethod
    def get_birthday(self, period):
        """
        Abstract method
        """

    @abstractmethod
    def update_contact(self, contact_id, contact):
        """
        Abstract method
        """

    @abstractmethod
    def insert_contact(self, contact):
        """
        Abstract method
        """

    @abstractmethod
    def delete_contact(self, contact_id):
        """
        Abstract method
        """


class ContactbookMongo(Contactbook):
    """
    Class  - list for Contacts.
    Connected to mongodb
    """

    def __init__(self, contact_db, counter_db):
        """
        Initilizing connection to MongoDB
        :param contact_db: Mongo collection
        :param counter_db: Mongo collection
        """
        super().__init__()
        self.contacts = []
        self.contact_db = contact_db
        self.counter_db = counter_db

    @LRU_cache(1)
    def get_all_contacts(self):
        """
        Get all contacts from mongodb collection
        :return: list of ContactMongo
        """
        self.contacts = []
        try:
            result = self.contact_db.find({}).sort("contact_id")
            for res in result:
                self.contacts.append(ContactMongo(res))
            return self.contacts
        except Exception as error:
            return str(error)

    @LRU_cache(10)
    def get_contacts(self, key):
        """
        Get contacts from mongodb collection find by keyword
        :return: list of ContactMongo
        """
        self.contacts = []
        if key != "":
            try:
                rgx = re.compile(f".*{key}.*", re.IGNORECASE)
                result = self.contact_db.find(
                    {"$or": [{"name": rgx}, {"phone": rgx}]}
                ).sort("contact_id")
                for res in result:
                    self.contacts.append(ContactMongo(res))
                return self.contacts
            except Exception as error:
                return str(error)
        else:
            return []

    @LRU_cache(10)
    def get_contact_details(self, contact_id):
        """
        Get contact from mongodb collection find by contact_id
        :param: contact_id: str
        :return: instance of ContactMongo
        """
        try:
            res = self.contact_db.find_one({"contact_id": int(contact_id)})
            if res is not None:
                contact = ContactMongo(res)
                return contact
            return res
        except Exception as error:
            return str(error)

    @LRU_cache(100)
    def get_birthday(self, period):
        """
        Get contacts from mongodb collection which birthday is
        in the period.
        :param: period: int
        :return: list of ContactMongo
        """
        self.contacts = []
        try:
            result = self.contact_db.aggregate(
                [
                    {
                        "$match": {
                            "$expr": {
                                "$in": [
                                    {
                                        "$substr": [
                                            {
                                                "$dateToString": {
                                                    "format": "%d.%m.%Y",
                                                    "date": "$birthday",
                                                }
                                            },
                                            0,
                                            5,
                                        ]
                                    },
                                    [
                                        (datetime.today() + timedelta(days=i)).strftime(
                                            "%d.%m.%Y"
                                        )[0:5]
                                        for i in range(1, period + 1)
                                    ],
                                ]
                            }
                        }
                    }
                ]
            )
            for res in result:
                contact_ = ContactMongo(res)
                contact_.celebrate = contact_.birthday[0:5]
                self.contacts.append(contact_)
                self.contacts = sorted(self.contacts, key=self.distance)
            return self.contacts
        except Exception as error:
            return str(error)

    @staticmethod
    def distance(contact):
        """
        Sorting key function
        :param: contact: ContactMongo
        :return: distance.days
        """
        try:
            test_date = date(
                date.today().year,
                datetime.strptime(contact.birthday, "%d.%m.%Y").month,
                datetime.strptime(contact.birthday, "%d.%m.%Y").day,
            )
        except ValueError:
            # for 29 february case
            test_date = date(
                date.today().year,
                datetime.strptime(contact.birthday, "%d.%m.%Y").month + 1,
                1,
            )
        if test_date < date.today():
            try:
                test_date = date(
                    date.today().year + 1,
                    datetime.strptime(contact.birthday, "%d.%m.%Y").month,
                    datetime.strptime(contact.birthday, "%d.%m.%Y").day,
                )
            except ValueError:
                # for 29 february case
                test_date = date(
                    date.today().year + 1,
                    datetime.strptime(contact.birthday, "%d.%m.%Y").month + 1,
                    1,
                )
        distance = test_date - date.today()
        return distance.days

    @LRU_cache_invalidate(
        "get_contacts", "get_all_contacts", "get_contact_details", "get_birthday"
    )
    def update_contact(self, contact_id, contact):
        """
        Update contact selectd by contact_id with data from param contact
        :param contact_id: int
        :param contact: ContactDict
        :return: 0 or error
        """
        try:
            self.contact_db.replace_one(
                {"contact_id": int(contact_id)},
                {
                    "contact_id": int(contact_id),
                    "name": contact.name,
                    "birthday": contact.birthday,
                    "created_at": contact.created_at,
                    "phone": contact.phone,
                    "email": contact.email,
                    "address": {
                        "zip": contact.zip,
                        "country": contact.country,
                        "region": contact.region,
                        "city": contact.city,
                        "street": contact.street,
                        "house": contact.house,
                        "apartment": contact.apartment,
                    },
                },
            )
            return 0
        except Exception as error:
            return error

    @LRU_cache_invalidate(
        "get_contacts", "get_all_contacts", "get_contact_details", "get_birthday"
    )
    def insert_contact(self, contact):
        """
        Insert new contact to postgres DB
        :param contact: ContactDict
        :return: 0 or error
        """
        test_contact = self.contact_db.find_one(
            {"name": contact.name, "birthday": contact.birthday}
        )
        if not test_contact:
            try:
                counter = self.counter_db.find_one(
                    {"counter_name": "contact_id"}, {"value": 1}
                )["value"]
                self.counter_db.replace_one(
                    {"counter_name": "contact_id"},
                    {"counter_name": "contact_id", "value": counter + 1},
                )
                self.contact_db.insert_one(
                    {
                        "contact_id": counter + 1,
                        "name": contact.name,
                        "birthday": contact.birthday,
                        "created_at": contact.created_at,
                        "phone": contact.phone,
                        "email": contact.email,
                        "address": {
                            "zip": contact.zip,
                            "country": contact.country,
                            "region": contact.region,
                            "city": contact.city,
                            "street": contact.street,
                            "house": contact.house,
                            "apartment": contact.apartment,
                        },
                    }
                )
                return 0
            except Exception as error:
                return f"Some problem: {str(error)}"
        else:
            return "Error creating the contact: contact already exists"

    @LRU_cache_invalidate(
        "get_contacts", "get_all_contacts", "get_contact_details", "get_birthday"
    )
    def delete_contact(self, contact_id):
        """
        Delete contact from postgres DB selected by contact_id
        :param contact_id: int
        :return: 0 or Error
        """
        try:
            self.contact_db.delete_one({"contact_id": int(contact_id)})
            return 0
        except Exception as error:
            return error


class ContactbookPSQL(Contactbook):
    """
    ContactBook - class conained in self.contacts Contact entities.
    Self.session stored connection to DB

    """

    def __init__(self, session=None):
        """
        Init class instance with connection to PostgreSQL
        :param session: pgsession
        """
        super().__init__()
        self.contacts = []
        self.session = session

    @LRU_cache(10)
    def get_all_contacts(self):
        """
        Get all the contacts from postgres DB
        :return: list(ContactPSQL) or error
        """
        self.contacts = []
        try:
            result = (
                self.session.query(Contact.contact_id, Contact.name, Contact.birthday)
                .order_by(Contact.contact_id)
                .all()
            )
            for res in result:
                self.contacts.append(ContactPSQL(res))
            return self.contacts
        except Exception as error:
            return str(error)

    @LRU_cache(10)
    def get_contacts(self, key):
        """
        Find contacts in postgres DB searching them by key in fields name and phone
        :param key: str
        :return: list(ContactsPSQL) or error
        """
        self.contacts = []
        try:
            if key != "":
                result = (
                    self.session.query(
                        Contact.contact_id,
                        Contact.name,
                        Contact.birthday,
                    )
                    .outerjoin(Phone_)
                    .filter(
                        or_(
                            func.lower(Contact.name).like(func.lower(f"%{key}%")),
                            func.lower(Phone_.phone).like(func.lower(f"%{key}%")),
                        )
                    )
                    .distinct()
                    .order_by(Contact.contact_id)
                    .all()
                )
                for res in result:
                    self.contacts.append(ContactPSQL(res))
                return self.contacts
            return []
        except Exception as error:
            return str(error)

    @LRU_cache(10)
    def get_contact_details(self, contact_id):
        """
        Select all contact data from joined tables in PostgreSQL DB. Data selected by contact_id.
        :param contact_id: int
        :return: ContactDetails
        """
        try:
            contact = self.session.query(
                Contact.contact_id, Contact.name, Contact.birthday
            ).filter(Contact.contact_id == contact_id)
            phone = self.session.query(Phone_.phone).filter(Phone_.contact_id == contact_id)
            email = self.session.query(Email_.email).filter(Email_.contact_id == contact_id)
            address = self.session.query(Address_).filter(Address_.contact_id == contact_id)
            return ContactDetails(contact[0], phone, email[0], address[0])
        except Exception as error:
            return str(error)


    @LRU_cache(100)
    def get_birthday(self, period):
        """
        Select all contacts from PostgreSQL database with birthday date in period
        :param period: int
        :return: list(ContactPSQL) or error
        """
        try:
            days = [
                (datetime.now() + timedelta(days=i)).strftime("%m-%d")
                for i in range(1, period + 1)
            ]
            res_list = []
            result = (
                self.session.query(Contact.contact_id, Contact.name, Contact.birthday)
                .filter(
                    func.substr(func.to_char(Contact.birthday, "YYYY-mm-dd"), 6, 10).like(
                        any_(days)
                    )
                )
                .all()
            )
            for res in result:
                res_list.append(res)
            res_list = sorted(res_list, key=self.distance)
            for res in res_list:
                contact = ContactPSQL(res)
                contact.celebrate = res.birthday.strftime("%d.%m")
                self.contacts.append(contact)
            return self.contacts
        except Exception as error:
            return str(error)

    @staticmethod
    def distance(contact):
        """
        Key function for sorting contact list by birthday celebration
        :param contact: ContactPSQL
        :return: distance.days: int
        """
        try:
            test_date = date(
                date.today().year, contact.birthday.month, contact.birthday.day
            )
        except ValueError:
            # for 29 february case
            test_date = date(date.today().year, contact.birthday.month + 1, 1)
        if test_date < date.today():
            try:
                test_date = date(
                    date.today().year + 1, contact.birthday.month, contact.birthday.day
                )
            except ValueError:
                # for 29 february case
                test_date = date(date.today().year + 1, contact.birthday.month + 1, 1)
        distance = test_date - date.today()
        return distance.days

    @LRU_cache_invalidate(
        "get_contacts", "get_all_contacts", "get_contact_details", "get_birthday"
    )
    def update_contact(self, contact_id, contact):
        """
        Update the contact in PostgreSQL DB, selected by contact_id with data from contact param
        :param contact_id: int
        :param contact: ContactDict
        :return: 0 or error
        """
        try:
            self.session.execute(
                update(
                    Contact,
                    values={
                        Contact.name: contact.name,
                        Contact.birthday: contact.birthday,
                    },
                ).filter(Contact.contact_id == contact_id)
            )
            self.session.commit()
            stmt = delete(Phone_).where(Phone_.contact_id == contact_id)
            self.session.execute(stmt)
            self.session.commit()
            for phone_num in contact.phone:
                phone = Phone_(contact_id=contact_id, phone=phone_num)
                self.session.add(phone)
            stmt = delete(Address_).where(Address_.contact_id == contact_id)
            self.session.execute(stmt)
            address = Address_(
                zip=contact.zip,
                country=contact.country,
                region=contact.region,
                city=contact.city,
                street=contact.street,
                house=contact.house,
                apartment=contact.apartment,
                contact_id=contact_id,
            )
            email = Email_(email=contact.email, contact_id=contact_id)
            self.session.add(address)
            stmt = delete(Email_).where(Email_.contact_id == contact_id)
            self.session.execute(stmt)
            self.session.commit()
            self.session.add(email)
            self.session.commit()
            return 0
        except Exception as error:
            return error
        finally:
            self.session.rollback()

    @LRU_cache_invalidate(
        "get_contacts", "get_all_contacts", "get_contact_details", "get_birthday"
    )
    def insert_contact(self, contact):
        """
        Insert new contact to PostgreSQL
        :param contact: ContactDict
        :return: 0 or error
        """
        try:
            contact_ = Contact(
                name=contact.name, created_at=date.today(), birthday=contact.birthday
            )
            self.session.add(contact_)
            self.session.commit()
        except Exception as error:
            return error
        finally:
            self.session.rollback()
        try:
            for phone_num in [phone_.strip() for phone_ in contact.phone]:
                phone = Phone_(contact_id=contact_.contact_id, phone=phone_num)
                self.session.add(phone)
            address = Address_(
                zip=contact.zip,
                country=contact.country,
                region=contact.region,
                city=contact.city,
                street=contact.street,
                house=contact.house,
                apartment=contact.apartment,
                contact_id=contact_.contact_id,
            )
            email = Email_(email=contact.email, contact_id=contact_.contact_id)
            self.session.add(address)
            self.session.add(email)
            self.session.commit()
        except Exception as error:
            return error
        finally:
            self.session.rollback()
        return 0

    @LRU_cache_invalidate(
        "get_contacts", "get_all_contacts", "get_contact_details", "get_birthday"
    )
    def delete_contact(self, contact_id):
        """
        Delete record from Contact table and cascade deleting all the records
        from Phone, Email, Address tables. Contact identified by contact_id.
        :param id: int
        :return: 0 or error
        """
        sql_stmt = delete(Contact).where(Contact.contact_id == contact_id)
        return run_sql(self.session, sql_stmt)

class ContactAbstract(ABC):
    """
    Abstract class for Contact Entities
    """

    @abstractmethod
    def __init__(self):
        pass


class ContactMongo(ContactAbstract):
    """
    Contact initialized using Mongo document
    """

    def __init__(self, json):
        super().__init__()
        self.name = json["name"]
        self.created_at = datetime.today()
        self.contact_id = json["contact_id"]
        if json["birthday"] == "" or json["birthday"] is None:
            self.birthday = ""
        else:
            self.birthday = json["birthday"].date().strftime("%d.%m.%Y")
        self.phone = json["phone"]
        self.email = json["email"]
        self.zip = json["address"]["zip"]
        self.country = json["address"]["country"]
        self.region = json["address"]["region"]
        self.city = json["address"]["city"]
        self.street = json["address"]["street"]
        self.house = json["address"]["house"]
        self.apartment = json["address"]["apartment"]
        self.celebrate = ""


class ContactPSQL(ContactAbstract):
    """
    Contact class initialized using SQLAlchemy query object
    """

    def __init__(self, contact):
        super().__init__()
        self.contact_id = contact.contact_id
        self.name = contact.name
        self.birthday = contact.birthday.strftime("%d.%m.%Y")
        self.celebrate = ""


class ContactDetails(ContactPSQL):
    """
    Contact details class initialized using SQLAlchemy query object
    """

    def __init__(self, contact, phones, email, address):
        super().__init__(contact)
        self.phone = []
        for phone in phones:
            self.phone.append(phone.phone)
        self.email = email.email
        self.zip = address.zip
        self.country = address.country
        self.region = address.region
        self.city = address.city
        self.street = address.street
        self.house = address.house
        self.apartment = address.apartment
        self.celebrate = ""


class ContactDict(ContactAbstract):
    """
    Contact class initialized using  dictionary
    """

    def __init__(self, form_dict):
        super().__init__()
        self.contact_id = None
        self.name = form_dict["Name"]["value"]
        self.birthday = form_dict["Birthday"]["value"]
        self.created_at = datetime.today()
        self.phone = [
            phone_.strip() for phone_ in form_dict["Phone"]["value"].split(",")
        ]
        self.email = form_dict["Email"]["value"]
        self.zip = form_dict["ZIP"]["value"]
        self.country = form_dict["Country"]["value"]
        self.region = form_dict["Region"]["value"]
        self.city = form_dict["City"]["value"]
        self.street = form_dict["Street"]["value"]
        self.house = form_dict["House"]["value"]
        self.apartment = form_dict["Apartment"]["value"]
