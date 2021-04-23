# EPLab

Программное обеспечение для работы с устройствами линейки EyePoint, предназначенными для поиска неисправностей на печатных платах в ручном режиме (при помощи ручных щупов).

## Установка в Windows

Установить MSVC 2013 redistributable (разрядность должна совпадать с разрядностью python).
https://www.microsoft.com/en-us/download/details.aspx?id=40784

Установить зависимости для python:

```
python -m pip install -r requirements.txt --upgrade
```
Выше приведён случай для установки на чистый Python.

Если в системе Python уже используется, желательно поставить все зависимости в виртуальное окружение:

```
python -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt --upgrade
```

Если у вас возникла такая ошибка: qt.qpa.plugin: Could not find the Qt platform plugin "windows" in "" 
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
Выполните следующую команду в виртуальном окружении:

```
set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
```

Для работы нужно установить драйвер `ivm.inf` из папки `release_templates\win64\driver`.

## Установка в Linux

Установить библиотеки для работы со звуком и для сборки пакетов python:

```
sudo apt-get install -y python3-dev libasound2-dev
```

Установить зависимости для python:

```
python3 -m pip install -r requirements.txt --upgrade
```
Выше приведён случай для установки на чистый Python.

Если в системе Python уже используется, желательно поставить все зависимости в виртуальное окружение:

```
python3 -m venv venv
venv/bin/python3 -m pip install --upgrade pip
venv/bin/python3 -m pip install -r requirements.txt --upgrade
```

Если при установке зависимостей через hg возникает ошибка авторизации, то нужно прописать в Hg логин и пароль от репозитория hg.ximc.ru. Это можно сделать через TortoiseHg, открыв любой репозиторий, перейдя во вкладку синхронизации (две стрелочки по кругу на верхней панели) и нажав на иконку с изображением замка (в середине страницы, слева от строки с адресом сервера). 

После этого нужно переоткрыть консоль.

Если у вас возникла такая ошибка: qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
Выполните следующие команды:

```
export QT_DEBUG_PLUGINS=1
sudo apt-get install --reinstall libxcb-xinerama0
```

Также нужен доступ на hg.ximc.ru к репозиториям: epcore, ivviewer.
Если при подключении вахометров они не обнаруживаются , то стоит прописать в системе VID и PID устройства для драйвера виртуального COM-порта. 
В Ubuntu это можно сделать так:

```
sudo sh -c 'echo 1CBC 0007 > /sys/bus/usb/drivers/cdc_acm/new_id'
```

Для корректной работы ПО с COM-портами, пользователь должен находиться в группе dealout.
Если при открытии устройств возникают какие-то проблемы, попробуйте запустить ПО с правами root.

## Запуск в Windows
```
python main.py <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать не обязательно).

`ivm_url` обычно - это адрес COM-порта. Также `ivm_url` может быть `virtual` (будет использоваться виртуальный измеритель).

Пример запуска:

```
python main.py com:\\.\COM13 --ref virtual
```

Если используется виртуальное окружение, то запускать нужно так:

```
venv\Scripts\python main.py com:\\.\COM13 --ref virtual
```

ПО предоставляет возможность работать с устройствами IVM10 и ASA (Meridian) по отдельности. Чтобы запустить приложение для работы с сетевым вахометром ASA нужно выполнить команду:

```
venv\Scripts\python main.py xmlrpc:172.16.3.213 --ref virtualasa --config eplab_asa_options.json
```

Здесь предполагается, что:

- сервер вахометра имеет IP адрес 172.16.3.213 и прослушивает порт 8888;
- совместно вахометром ASA запускается виртуальный вахометр (за это отвечает аргумент virtualasa);
- ПО получает файл с конфигурацией `eplab_asa_options.json` для работы с вахометром ASA.

## Запуск в Linux

```
python3 main.py <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать не обязательно).

`ivm_url` обычно - это адрес COM-порта. Также `ivm_url` может быть `virtual` (будет использоваться виртуальный измеритель).

Пример запуска:

```
python3 main.py com:///dev/ttyACM0 --ref virtual
```

Если используется виртуальное окружение, то запускать нужно так:

```
venv/bin/python3 main.py com:///dev/ttyACM0 --ref virtual
```

Если хотите изменить язык, то нужно добавить/убрать флаг --en:
```
python3 main.py com:///dev/ttyACM0 --ref virtual --en
```

## Релиз

Для релиза есть скрипт release.cmd. В нём нужно прописать путь до системного 
интерпретатора Python**3.6** **x64**. Для запуска в консоли набрать:

```
release.bat
```
Собранный релиз будет лежать в папке dist

На Linnux нужно выполнить

```
release.sh
```

## Запуск тестов

```
venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

## Дополнительно

Файл платы для тестов можно загрузить из папки  `tests\test_data\eyepoint_calibration_board`.

Чтобы сконвертировать файлы плат, сделанные с помощью EyePoint Px, можно воспользоваться конвертером, который находится в модуле `epcore.utils`.

