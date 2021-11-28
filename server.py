"""

"""
import socket
import sys
import argparse
import json
import logging
import select
import time
import logs.config_server_log
from errors import IncorrectDataRecivedError
from common.variables import *
from common.utils import *
from decos import log
from descripts import Port, Host
from metaclasses import MetaServer
from server_database import ServerStorage

# Инициализация логирования сервера.
logger = logging.getLogger('server')


class Server(metaclass=MetaServer):
    """

    """
    port = Port()
    host = Host()

    def __init__(self, database, transport=None):
        self.host, self.port = self.arg_parser()
        self.database = database
        self.names = dict()
        if not transport:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.transport = transport

    @log
    def arg_parser(self) -> tuple:
        """
        Парсер аргументов коммандной строки.
        :return: tuple(listen_address, listen_port)
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('-p', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-a', default='', nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        listen_address = namespace.a
        listen_port = namespace.p

        # проверка получения корретного номера порта для работы сервера.
        if not 1023 < listen_port < 65536:
            logger.critical(
                f'Попытка запуска сервера с указанием неподходящего порта {listen_port}. '
                f'Допустимы адреса с 1024 до 65535.')
            exit(1)

        return listen_address, listen_port

    @log
    def connect(self, host=None, port=None) -> None:
        """

        :param host: str
        :param port: int
        :return: None
        """
        host = self.host if not host else host
        port = self.port if not port else port
        logger.info(
            f'Запущен сервер, порт для подключений: {port} , '
            f'адрес с которого принимаются подключения: {host}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')
        self.transport.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.transport.bind((host, port))
        self.transport.settimeout(0.5)


    @log
    def listen(self) -> None:
        """

        :return:
        """
        # список клиентов , очередь сообщений
        clients = []
        messages = []
        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        names = dict()

        # Слушаем порт
        ## self.transport.listen(MAX_CONNECTIONS)
        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = self.transport.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соедение с ПК {client_address}')
                clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов
            try:
                if clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(clients, clients, [], 0)
            except OSError:
                pass

            # принимаем сообщения и если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        self.process_client_message(get_message(client_with_message), messages, client_with_message,
                                                    clients,
                                                    names)
                    except:
                        logger.info(f'Клиент {client_with_message.getpeername()} отключился от сервера.')
                        clients.remove(client_with_message)

            # Если есть сообщения, обрабатываем каждое.
            for i in messages:
                try:
                    self.process_message(i, names, send_data_lst)
                except:
                    logger.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                    clients.remove(names[i[DESTINATION]])
                    del names[i[DESTINATION]]
            messages.clear()

    @log
    def process_client_message(self, message, messages_list, client, clients, names) -> None:
        """
         Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента, проверяет корректность, отправляет
         словарь-ответ в случае необходимости.
        :param messages_list:
        :param client:
        :param clients:
        :param names:
        :return:
        """
        logger.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем,
            # иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in names.keys():
                self.names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.database.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            messages_list.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.database.user_logout(message[ACCOUNT_NAME])
            clients.remove(names[ACCOUNT_NAME])
            names[ACCOUNT_NAME].close()
            del names[ACCOUNT_NAME]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return

    @log
    def process_message(self, message, names, listen_socks) -> None:
        """
        Функция адресной отправки сообщения определённому клиенту.
        Принимает словарь сообщение, список зарегистрированых
        пользователей и слушающие сокеты. Ничего не возвращает.
        :param message:
        :param names:
        :param listen_socks:
        :return:
        """
        if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
            send_message(names[message[DESTINATION]], message)
            logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, отправка сообщения невозможна.')


def print_help():
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключенных пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    database = ServerStorage()
    transport = Server(database)
    transport.connect()
    # transport.listen()
    while True:
        command = input('Введите комманду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input(
                'Введите имя пользователя для просмотра истории. Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()
