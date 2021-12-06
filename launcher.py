import subprocess

process = []

while True:
    action = input('Выберите действие: q - выход , s - запустить сервер и клиенты, x - закрыть все окна:')

    if action == 'q':
        break
    elif action == 's':
        process.append(subprocess.Popen('python3 server_run.py', shell=True))
        process.append(subprocess.Popen('python3 client.py', shell=True))
        process.append(subprocess.Popen('python3 client.py', shell=True))
        process.append(subprocess.Popen('python3 client.py', shell=True))
    elif action == 'x':
        while process:
            victim = process.pop()
            victim.kill()