# EPLab

Программное обеспечение для работы с устройствами линейки EyePoint, предназначенными для поиска неисправностей на печатных платах в ручном режиме (при помощи ручных щупов).

## Установка в Windows

1. Установите [MSVC 2013 redistributable](https://www.microsoft.com/en-us/download/details.aspx?id=40784) (разрядность должна совпадать с разрядностью Python).

2. Установите зависимости для Python, запустив скрипт `rebuild_venv.bat`:

   ```bash
   rebuild_venv.bat
   ```

3. В зависимости от разрядности вашей ОС установите драйвер `ivm.inf` из папки `resources\win32\drivers\ivm` или `resources\win64\drivers\ivm`.

4. Если вы планируете использовать мультиплексор, установите драйвер `epmux.inf` из папки `resources\win32\drivers\epmux` или `resources\win64\drivers\epmux` в зависимости от разрядности вашей ОС.

## Установка в Linux

1. Установите библиотеку `libcurl`:

   ```bash
   sudo apt-get update
   sudo apt-get install libcurl3
   sudo apt-get install libcurl4-openssl-dev
   ```

2. Установите библиотеки для работы со звуком и для сборки пакетов Python:

   ```bash
   sudo apt-get install -y python3-dev libasound2-dev
   ```

3. Установить зависимости для Python, выполнив скрипт `rebuild_venv.sh`:

   ```bash
   bash rebuild_venv.sh
   ```

## Примечание к установке в Windows и Linux

Для установки всех необходимых зависимостей нужен доступ на https://gitlab.ximc.ru к репозиториям [epcore](https://gitlab.ximc.ru/eyepoint/epcore) и [ivviewer](https://gitlab.ximc.ru/eyepoint/ivviewer) и доступ на https://github.com к репозиторию [ep_report_generator](https://github.com/EPC-MSU/ep_report_generator/).

Чтобы установить зависимости через `git`:

1. Следуя [инструкциям](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token), получите `access_token`.

2. В файле `requirements.txt` замените строчку с `ep_report_generator` на следующую (здесь `username` - имя пользователя в https://github.com):

   ```bash
   git+https://username:access_token@github.com/EPC-MSU/ep_report_generator@vX.X.X#egg=ep_report_generator
   ```

## Запуск в Windows

ПО предоставляет возможность работать с устройствами IVM10 и АСА (Meridian) по отдельности.

#### Запуск в Windows для работы с IVM10

Чтобы запустить приложение для работы с устройствами IVM10, нужно выполнить команду:

```bash
venv\Scripts\python main.py <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать не обязательно). `ivm_url`  - это адрес COM-порта. Также `ivm_url` может быть `virtual` (будет использоваться виртуальный измеритель). Пример запуска:

```bash
venv\Scripts\python main.py com:\\.\COM13 --ref virtual
```

Для запуска ПО для работы с устройствами типа IVM10 можно использовать скрипт `run.bat`, в котором нужно прописать адреса COM-портов, к которым подключены устройства:

```bash
run.bat
```

#### Запуск в Windows для работы с АСА

Чтобы запустить приложение для работы с сетевым устройством АСА, нужно выполнить команду:

```bash
venv\Scripts\python main.py xmlrpc://172.16.3.213 --ref virtualasa --config eplab_asa_options.json
```

Здесь предполагается, что:

- сервер устройства АСА имеет IP адрес 172.16.3.213 и прослушивает порт 8888;
- совместно с устройством АСА запускается виртуальный измеритель (за это отвечает аргумент `virtualasa`);
- ПО получает файл с конфигурацией `eplab_asa_options.json` для работы с устройством АСА.

Для запуска ПО для работы с устройством АСА можно использовать скрипт `run.bat`, в котором нужно прописать IP адрес сервера и добавить путь к config-файлу:

```bash
run.bat
```

#### Возможные ошибки при запуске в Windows

Если у вас возникла такая ошибка:

```bash
qt.qpa.plugin: Could not find the Qt platform plugin "windows" in "" 
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
```

выполните следующую команду в виртуальном окружении:

```bash
set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
```

## Запуск в Linux

ПО предоставляет возможность работать с устройствами IVM10 и АСА (Meridian) по отдельности.

#### Запуск в Linux для работы с IVM10

Чтобы запустить приложение для работы с устройствами IVM10, нужно выполнить команду:

```bash
venv/bin/python3 main.py <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать не обязательно). `ivm_url`  - это адрес COM-порта. Также `ivm_url` может быть `virtual` (будет использоваться виртуальный измеритель). Пример запуска:

```bash
venv/bin/python3 main.py com:///dev/ttyACM0 --ref virtual
```

Для запуска ПО для работы с устройствами типа IVM10 можно использовать скрипт `run.sh`, в котором нужно прописать адреса COM-портов, к которым подключены устройства:

```bash
bash run.sh
```

#### Запуск в Linux для работы с АСА

Чтобы запустить приложение для работы с сетевым устройством АСА, нужно выполнить команду:

```bash
venv/bin/python3 main.py xmlrpc://172.16.3.213 --ref virtualasa --config eplab_asa_options.json
```

Здесь предполагается, что:

- сервер устройства АСА имеет IP адрес 172.16.3.213 и прослушивает порт 8888;
- совместно с устройством АСА запускается виртуальный измеритель (за это отвечает аргумент `virtualasa`);
- ПО получает файл с конфигурацией `eplab_asa_options.json` для работы с устройством АСА.

Для запуска ПО для работы с устройством АСА можно использовать скрипт `run.sh`, в котором нужно прописать IP адрес сервера и добавить путь к config-файлу:

```bash
bash run.sh
```

#### Возможные ошибки при запуске в Linux

1. Если при подключении измерители не обнаруживаются, то стоит прописать в системе VID и PID устройства для драйвера виртуального COM-порта:

   ```bash
   sudo sh -c 'echo 1CBC 0007 > /sys/bus/usb/drivers/cdc_acm/new_id'
   ```

2. Для корректной работы ПО с COM-портами пользователь должен находиться в группе `dialout`. Чтобы добавить пользователя в эту группу, выполните команду (здесь предполагается, что имя пользователя `username`):

   ```bash
   sudo adduser username dialout
   ```

   После добавления пользователя в группу `dialout` перезагрузите компьютер.

3. Если при открытии устройств все же возникают какие-то проблемы, попробуйте запустить ПО с правами `root`.

4. Если у вас возникла такая ошибка:

   ```bash
   qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
   ```

   выполните следующие команды:

   ```bash
   export QT_DEBUG_PLUGINS=1
   sudo apt-get install --reinstall libxcb-xinerama0
   ```

## Запуск тестов в Windows

Для запуска тестов нужно выполнить скрипт `testall.bat`:

```bash
testall.bat
```

## Запуск тестов в Linux

Для запуска тестов нужно выполнить скрипт `testall.sh`:

```bash
bash testall.sh
```

## Выпуск релиза в Windows

Для выпуска релиза в Windows нужно выполнить скрипт `release.bat`:

```bash
release.bat
```

ВНИМАНИЕ! Релиз нужно выпустить на Windows 7.

## Выпуск релиза в Linux

Для выпуска релиза в Linux нужно выполнить скрипт `release.sh`:

```bash
bash release.sh
```

ВНИМАНИЕ! Релиз нужно выпустить на Ubuntu 18.

## Дополнительно

- Файл платы для тестов можно загрузить из папки  `tests\test_data\eyepoint_calibration_board`.

- Чтобы сконвертировать файлы плат, сделанные с помощью `EyePoint Px`, можно воспользоваться конвертером, который находится в модуле `epcore.utils`.

- Для работы с сетевым устройством АСА нужно запустить сервер версии 4.3.2.

- Для корректной работы приложения необходимо отключить брандмауэр (firewall) на компьютере.

- Для корректной работы приложения на виртуальной машине нужно настроить сеть виртуальной машины. Для этого выберите виртуальную машину:

  ```bash
  Настроить -> Сеть -> Адаптер 1 -> Включить сетевой адаптер -> Тип подключения -> Сетевой мост
  ```

  Аналогично нужно настроить адаптер 2:
  
  ```bash
  Настроить -> Сеть -> Адаптер 2 -> Включить сетевой адаптер -> Тип подключения -> NAT
  ```
  
  
