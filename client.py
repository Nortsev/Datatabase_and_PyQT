"""

"""
import sys
import json
import socket
import time
import argparse
import logging
import threading
import logs.config_client_log
from common.variables import *
from common.utils import *
from errors import IncorrectDataRecivedError, ReqFieldMissingError, ServerError
from decos import log
from metaclasses import MetaClient

# Инициализация клиентского логера
logger = logging.getLogger('client')


class Client(metaclass=MetaClient):
    """

    """
    def __init__(self, transport=None):
        self.host, self.port, self.client_name = self.arg_parser()
        if not transport:
            self.transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.transport = transport
        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if not self.client_name:
            self.client_name = input('Введите имя пользователя: ')

    @log
    def arg_parser(self) -> tuple:
        """
        Парсер аргументов коммандной строки
        :return:
        """
        parser = argparse.ArgumentParser()
        parser.add_argument('addr', default=DEFAULT_IP_ADDRESS, nargs='?')
        parser.add_argument('port', default=DEFAULT_PORT, type=int, nargs='?')
        parser.add_argument('-n', '--name', default=None, nargs='?')
        namespace = parser.parse_args(sys.argv[1:])
        server_address = namespace.addr
        server_port = namespace.port
        client_name = namespace.name

        # проверим подходящий номер порта
        if not 1023 < server_port < 65536:
            logger.critical(
                f'Попытка запуска клиента с неподходящим номером порта: {server_port}. Допустимы адреса с 1024 до 65535. Клиент завершается.')
            exit(1)

        return server_address, server_port, client_name

    @log
    def connect(self, host=None, port=None, client_name=None) -> None:
        """

        :return:
        """
        host = self.host if not host else host
        port = self.port if not port else port
        client_name = self.port if not client_name else client_name
        self.transport.connect((host, port))
        logger.info(
            f'Запущен клиент с парамертами: адрес сервера: {host} , '
            f'порт: {port}, имя пользователя: {client_name}')

    @log
    def create_exit_message(self, account_name) -> dict:
        """
        Функция создаёт словарь с сообщением о выходе.
        :param account_name:
        :return:
        """
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: account_name
        }

    @log
    def message_from_server(self, sock, my_username) -> None:
        """
        Функция - обработчик сообщений других пользователей, поступающих с сервера.
        :param sock:
        :param my_username:
        :return:
        """
        while True:
            try:
                message = get_message(sock)
                if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == my_username:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                    logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                else:
                    logger.error(f'Получено некорректное сообщение с сервера: {message}')
            except IncorrectDataRecivedError:
                logger.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError, ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Потеряно соединение с сервером.')
                break

    @log
    def create_message(self, sock, account_name='Guest') -> None:
        """
        Функция запрашивает кому отправить сообщение и само сообщение, и отправляет полученные данные на сервер.
        :param sock:
        :param account_name:
        :return:
        """
        to = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: account_name,
            DESTINATION: to,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(sock, message_dict)
            logger.info(f'Отправлено сообщение для пользователя {to}')
        except:
            logger.critical('Потеряно соединение с сервером.')
            exit(1)

    @log
    def user_interactive(self, sock, username) -> None:
        """
         Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения
        :param sock:
        :param username:
        :return:
        """
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message(sock, username)
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                send_message(sock, self.create_exit_message(username))
                print('Завершение соединения.')
                logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    @log
    def create_presence(self, account_name) -> dict:
        """
        Функция генерирует запрос о присутствии клиента
        :param account_name:
        :return:
        """
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: account_name
            }
        }
        logger.debug(f'Сформировано {PRESENCE} сообщение для пользователя {account_name}')
        return out

    def print_help(self) -> None:
        """
        Функция выводящяя справку по использованию.
        :return:
        """
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    @log
    def process_response_ans(self, message) -> str:
        """
        Функция разбирает ответ сервера на сообщение о присутствии, возращает 200 если все ОК или генерирует исключение при\
        ошибке.
        :return:
        """
        logger.debug(f'Разбор приветственного сообщения от сервера: {message}')
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            elif message[RESPONSE] == 400:
                raise ServerError(f'400 : {message[ERROR]}')
        raise ReqFieldMissingError(RESPONSE)

    @log
    def send_msg(self) -> None:
        """
        Инициализация сокета и сообщение серверу о нашем появлении
        :return:
        """
        try:
            send_message(self.transport, self.create_presence(self.client_name))
            answer = self.process_response_ans(get_message(self.transport))
            logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером.')
        except json.JSONDecodeError:
            logger.error('Не удалось декодировать полученную Json строку.')
            exit(1)
        except ServerError as error:
            logger.error(f'При установке соединения сервер вернул ошибку: {error.text}')
            exit(1)
        except ReqFieldMissingError as missing_error:
            logger.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
            exit(1)
        except (ConnectionRefusedError, ConnectionError):
            logger.critical(
                f'Не удалось подключиться к серверу {self.host}:{self.port}, '
                f'конечный компьютер отверг запрос на подключение.')
            exit(1)
        else:
            # Если соединение с сервером установлено корректно,
            # запускаем клиенский процесс приёма сообщний
            receiver = threading.Thread(target=self.message_from_server, args=(self.transport, self.client_name))
            receiver.daemon = True
            receiver.start()

            # затем запускаем отправку сообщений и взаимодействие с пользователем.
            user_interface = threading.Thread(target=self.user_interactive, args=(self.transport, self.client_name))
            user_interface.daemon = True
            user_interface.start()
            logger.debug('Запущены процессы')

            # Watchdog основной цикл, если один из потоков завершён, то значит или потеряно соединение или пользователь
            # ввёл exit. Поскольку все события обработываются в потоках, достаточно просто завершить цикл.
            while True:
                time.sleep(1)
                if receiver.is_alive() and user_interface.is_alive():
                    continue
                break


def main():
    transport = Client()
    transport.connect()
    transport.send_msg()


if __name__ == '__main__':
    main()
