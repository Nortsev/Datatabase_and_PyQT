import datetime
from common.variables import *
from sqlalchemy import create_engine, Table, Column, Integer, String, Text, MetaData, DateTime
from sqlalchemy.orm import mapper, sessionmaker
import os


class ClientDatabase:
    """
    Класс - база данных сервера.
    """

    class KnownUsers:
        """
        Класс - отображение таблицы известных пользователей.
        """

        def __init__(self, user):
            self.id = None
            self.username = user

    class MessageStat:
        """
        Класс - отображение для таблицы статистики переданных сообщений.
        """

        def __init__(self, contact, direction, message):
            self.id = None
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.datetime.now()

    class Contacts:
        """
        Класс - отображение списка контактов
        """

        def __init__(self, contact):
            self.id = None
            self.name = contact

    def __init__(self, name):
        """
        Конструктор класса:
        :param name:
        """
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{name}.db3'
        self.database_engine = create_engine(
            f'sqlite:///{os.path.join(path, filename)}',
            echo=False,
            pool_recycle=7200,
            connect_args={
                'check_same_thread': False})

        self.metadata = MetaData()
        users = Table('known_users', self.metadata,
                      Column('id', Integer, primary_key=True),
                      Column('username', String)
                      )
        history = Table('message_history', self.metadata,
                        Column('id', Integer, primary_key=True),
                        Column('contact', String),
                        Column('direction', String),
                        Column('message', Text),
                        Column('date', DateTime)
                        )
        contacts = Table('contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('name', String, unique=True)
                         )
        self.metadata.create_all(self.database_engine)
        mapper(self.KnownUsers, users)
        mapper(self.MessageStat, history)
        mapper(self.Contacts, contacts)
        Session = sessionmaker(bind=self.database_engine)
        self.session = Session()
        self.session.query(self.Contacts).delete()
        self.session.commit()

    def add_contact(self, contact) -> None:
        """
        Функция добавления контактов
        :param contact:
        :return:
        """
        if not self.session.query(
            self.Contacts).filter_by(
                name=contact).count():
            contact_row = self.Contacts(contact)
            self.session.add(contact_row)
            self.session.commit()

    def del_contact(self, contact) -> None:
        """
        Функция удаления контакта
        :param contact:
        :return:
        """

        self.session.query(self.Contacts).filter_by(name=contact).delete()

    def contacts_clear(self) -> None:
        """
        Метод очищающий таблицу со списком контактов.
        :return:
        """
        self.session.query(self.Contacts).delete()

    def add_users(self, users_list) -> None:
        """
        Функция добавления известных пользователей.
        :param users_list:
        :return:
        """
        self.session.query(self.KnownUsers).delete()
        for user in users_list:
            user_row = self.KnownUsers(user)
            self.session.add(user_row)
        self.session.commit()

    def save_message(self, contact, direction, message) -> None:
        """
        Функция сохраняющяя сообщения
        :param contact:
        :param direction:
        :param message:
        :return:
        """
        message_row = self.MessageStat(contact, direction, message)
        self.session.add(message_row)
        self.session.commit()

    def get_contacts(self) -> list:
        """
        Функция возвращающяя контакты
        :return:
        """
        return [contact[0]
                for contact in self.session.query(self.Contacts.name).all()]

    def get_users(self) -> list:
        """
        Функция возвращающяя список известных пользователей
        :return:
        """
        return [user[0]
                for user in self.session.query(self.KnownUsers.username).all()]

    def check_user(self, user) -> bool:
        """
        Функция проверяющяя наличие пользователя в известных
        :param user:
        :return:
        """
        if self.session.query(
            self.KnownUsers).filter_by(
                username=user).count():
            return True
        else:
            return False

    def check_contact(self, contact) -> bool:
        """
        Функция проверяющяя наличие пользователя контактах
        :param contact:
        :return:
        """
        if self.session.query(self.Contacts).filter_by(name=contact).count():
            return True
        else:
            return False

    def get_history(self, contact) -> list:
        """
        Функция возвращающая историю переписки
        :param contact:
        :return:
        """
        query = self.session.query(
            self.MessageStat).filter_by(
            contact=contact)
        return [(history_row.contact,
                 history_row.direction,
                 history_row.message,
                 history_row.date) for history_row in query.all()]


if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    print(sorted(test_db.get_history('test2'), key=lambda item: item[3]))
