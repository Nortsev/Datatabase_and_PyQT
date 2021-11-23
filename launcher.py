import subprocess

process = []

while True:
    action = input('Выберите действие: q - выход , s - запустить сервер и клиенты, x - закрыть все окна:')

    if action == 'q':
        break
    elif action == 's':
        process.append(subprocess.Popen('python3 server.py', shell=True))
        process.append(subprocess.Popen('python3 client.py -n test1', shell=True))
        process.append(subprocess.Popen('python3 client.py -n test2', shell=True))
        process.append(subprocess.Popen('python3 client.py -n test3', shell=True))
    elif action == 'x':
        while process:
            victim = process.pop()
            victim.kill()