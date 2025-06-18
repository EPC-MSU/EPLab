# EPLab

Программное обеспечение для работы с устройствами линейки EyePoint, предназначенными для поиска неисправностей на печатных платах в ручном режиме (при помощи ручных щупов).

## Про ветки

Ветка dev-1.4 - основная. Ветка t-astra - для ОС Astra Linux.  В ветке t-astra не поддерживается измеритель ASA.
Все общие изменения нужно вносить сначала в ветку dev-1.4, а потом сливать в t-astra.

## Установка в Windows

1. Установите [MSVC 2013 redistributable](https://www.microsoft.com/en-us/download/details.aspx?id=40784) и [MSVC 2015 redistributable](https://www.microsoft.com/ru-ru/download/details.aspx?id=48145) (разрядность должна совпадать с разрядностью Python).

2. Установите зависимости для Python, перейдя в папку **scripts** и запустив скрипт **rebuild_venv.bat**.

3. В зависимости от разрядности вашей ОС установите драйвер **ivm.inf** из папки **resources\win32\drivers\ivm** или **resources\win64\drivers\ivm**.

4. Если Вы планируете использовать мультиплексор, установите драйвер **epmux.inf** из папки **resources\win32\drivers\epmux** или **resources\win64\drivers\epmux** в зависимости от разрядности вашей ОС.

## Установка в Ubuntu

1. Установите библиотеки для работы со звуком и для сборки пакетов Python:

   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-dev libasound2-dev
   ```

2. Установите зависимости для Python, перейдя в папку **scripts** и запустив скрипт **rebuild_venv.sh**:

   ```bash
   bash rebuild_venv.sh
   ```

## Установка в Astra Linux

1. Установка проводилась в *Astra Linux 2.12.22*.

2. В файле **/etc/apt/sources.list** закомментируйте все ранее записанные репозитории и добавьте репозиторий:

   ```
   deb https://mirror.yandex.ru/astra/frozen/2.12_x86-64/2.12.22/repository/ orel main contrib non-free
   ```

3. Установите библиотеки и пакеты для сборки Python из исходников:

   ```bash
   sudo apt update
   sudo apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev liblzma-dev libnss3-dev libssl-dev libsqlite3-dev libreadline-dev libffi-dev curl libbz2-dev python-tk python3-tk tk-dev
   ```

4. Скачайте исходники Python 3.6.8:

   ```bash
   wget https://www.python.org/ftp/python/3.6.8/Python-3.6.8.tgz
   ```

5. Разархивируйте скачанный архив:

   ```bash
   tar -xf Python-3.6.8.tgz
   ```

6. Перейдите в папку **Python-3.6.8**, в которой находятся разархивированные файлы, и выполните команды:

   ```bash
   cd Python-3.6.8
   ./configure --enable-optimizations --enable-shared --with-tcltk-includes='-I/usr/include -I/usr/include/tcl' --with-tcltk-libs='-L/usr/lib -ltcl -ltk'
   ```

7. Запустите сборку Python:

   ```bash
   make
   ```

8. После завершения сборки установите Python командой:

   ```bash
   sudo make altinstall
   ```

9. Выполните команду:

   ```bash
   sudo ldconfig -v
   ```

10. Установите библиотеки для работы со звуком и для сборки пакетов Python:

    ```bash
    sudo apt-get install -y python3-dev libasound2-dev
    ```

11. Установите зависимости для Python, перейдя в папку **scripts** и запустив скрипт **rebuild_venv.sh**:

    ```bash
    bash rebuild_venv.sh
    ```

## Запуск в Windows

ПО предоставляет возможность работать с устройствами IVM10 и АСА (Meridian) по отдельности.

#### Запуск в Windows для работы с IVM10

Чтобы запустить приложение для работы с устройствами IVM10, нужно выполнить команду:

```batch
venv\Scripts\python main.py --test <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать необязательно). *ivm_url*  - это адрес COM-порта. Также *ivm_url* может быть *virtual* (будет использоваться виртуальный измеритель). Пример запуска:

```batch
venv\Scripts\python main.py --test com:\\.\COM13 --ref virtual
```

#### Запуск в Windows для работы с АСА

Чтобы запустить приложение для работы с сетевым устройством АСА, нужно выполнить команду:

```batch
venv\Scripts\python main.py --test xmlrpc://172.16.3.213 --ref virtualasa --config eplab_asa_options.json
```

Здесь предполагается, что:

- сервер устройства АСА имеет IP адрес 172.16.3.213 и прослушивает порт 8888;
- совместно с устройством АСА запускается виртуальный измеритель (за это отвечает аргумент *virtualasa*);
- ПО получает файл с конфигурацией **eplab_asa_options.json** для работы с устройством АСА.

#### Запуск в Windows в общем случае

Приложение можно запустить, перейдя в папку **scripts** и запустив скрипт **run.bat**.

#### Возможные ошибки при запуске в Windows

Если у вас возникла такая ошибка:

> qt.qpa.plugin: Could not find the Qt platform plugin "windows" in "" 
> This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

выполните следующую команду в виртуальном окружении:

```batch
set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
```

## Запуск в Linux

ПО предоставляет возможность работать с устройствами IVM10 и АСА (Meridian) по отдельности.

#### Запуск в Linux для работы с IVM10

Чтобы запустить приложение для работы с устройствами IVM10, нужно выполнить команду:

```bash
venv/bin/python3 main.py --test <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать не обязательно). *ivm_url*  - это адрес COM-порта. Также *ivm_url* может быть *virtual* (будет использоваться виртуальный измеритель). Пример запуска:

```bash
venv/bin/python3 main.py --test com:///dev/ttyACM0 --ref virtual
```

#### Запуск в Linux для работы с АСА

Чтобы запустить приложение для работы с сетевым устройством АСА, нужно выполнить команду:

```bash
venv/bin/python3 main.py --test xmlrpc://172.16.3.213 --ref virtualasa --config eplab_asa_options.json
```

Здесь предполагается, что:

- сервер устройства АСА имеет IP адрес 172.16.3.213 и прослушивает порт 8888;
- совместно с устройством АСА запускается виртуальный измеритель (за это отвечает аргумент *virtualasa*);
- ПО получает файл с конфигурацией **eplab_asa_options.json** для работы с устройством АСА.

#### Запуск в Linux в общем случае

Приложение можно запустить, перейдя в папку **scripts** и запустив скрипт **run.sh**:

```bash
bash run.sh
```

#### Возможные ошибки при запуске в Linux

1. Если при подключении измерители не обнаруживаются, то стоит прописать в системе VID и PID устройства для драйвера виртуального COM-порта:

   ```bash
   sudo sh -c 'echo 1CBC 0007 > /sys/bus/usb/drivers/cdc_acm/new_id'
   ```

2. Для корректной работы ПО с COM-портами пользователь должен находиться в группе **dialout**. Чтобы добавить пользователя в эту группу, выполните команду (здесь предполагается, что имя пользователя *username*):

   ```bash
   sudo adduser username dialout
   ```

   После добавления пользователя в группу **dialout** перезагрузите компьютер.

3. Если при открытии устройств все же возникают какие-то проблемы, попробуйте запустить ПО с правами **root**.

4. Если у вас возникла такая ошибка:

   > qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
   
   выполните следующую команду:

   ```bash
   export QT_DEBUG_PLUGINS=1
   ```
   
   Запустите приложение еще раз. Возможно, отладочный уровень логирования поможет Вам понять, что дополнительно требуется для Qt.
   
   Возможно, Вам поможет установка следующих библиотек:
   
   ```bash
   sudo apt-get install --reinstall libxcb-xinerama0
   sudo apt-get install libxcb-randr0-dev libxcb-xtest0-dev libxcb-xinerama0-dev libxcb-shape0-dev libxcb-xkb-dev
   sudo apt-get install libxkbcommon-x11-dev
   ```
   
   Если у Вас не хватает *libxcb-util.so.1*, попробуйте:
   
   ```bash
   sudo ln -fs /usr/lib/x86_64-linux-gnu/libxcb-util.so.0.0.0 /usr/lib/x86_64-linux-gnu/libxcb-util.so.1.0.0
   sudo ln -fs /usr/lib/x86_64-linux-gnu/libxcb-util.so.0.0.0 /usr/lib/x86_64-linux-gnu/libxcb-util.so.1.0
   sudo ln -fs /usr/lib/x86_64-linux-gnu/libxcb-util.so.0.0.0 /usr/lib/x86_64-linux-gnu/libxcb-util.so.1
   ```

## Запуск тестов

Для запуска тестов перейдите в папку **scripts** и запустите скрипт:

- **run_tests.bat**, если Вы работаете в *Windows*;

- **run_tests.sh**, если Вы работаете в *Linux*:

  ```bash
  bash run_tests.sh
  ```

## Выпуск релиза

Для выпуска релиза перейдите в папку **scripts** и запустите скрипт:

- **release.bat**, если Вы работаете в *Windows* (**ВНИМАНИЕ! Релиз нужно выпускать на Windows 7**);

- **release.sh**, если Вы работаете в *Linux* (**ВНИМАНИЕ! Релиз нужно выпустить на Ubuntu 18**):

  ```bash
  bash release.sh
  ```

## Дополнительно

- Для работы с сетевым устройством АСА нужно запустить сервер версии >= 4.3.2.

- Для корректной работы приложения необходимо отключить брандмауэр (firewall) на компьютере.

- Для корректной работы приложения на виртуальной машине нужно настроить сеть виртуальной машины. Для этого выберите виртуальную машину:

  ```
  Настроить -> Сеть -> Адаптер 1 -> Включить сетевой адаптер -> Тип подключения -> Сетевой мост
  ```

  Аналогично нужно настроить адаптер 2:
  
  ```
  Настроить -> Сеть -> Адаптер 2 -> Включить сетевой адаптер -> Тип подключения -> NAT
  ```
  
  
