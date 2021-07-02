# EPLab

Программное обеспечение для работы с устройствами линейки EyePoint, предназначенными для поиска неисправностей на печатных платах в ручном режиме (при помощи ручных щупов).

## Установка в Windows

1. Установите MSVC 2013 redistributable (разрядность должна совпадать с разрядностью python) https://www.microsoft.com/en-us/download/details.aspx?id=40784.

2. Установите драйвер `ivm.inf` из папки `release_templates\win64\driver`.

3. Установить зависимости для Python, запустив скрипт `install_requirements.bat`:

   ```
   install_requirements.bat
   ```

Если у Вас возникла такая ошибка:

`qt.qpa.plugin: Could not find the Qt platform plugin "windows" in "" 
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem`
выполните следующую команду в виртуальном окружении:

```
set QT_QPA_PLATFORM_PLUGIN_PATH=venv\Lib\site-packages\PyQt5\Qt\plugins\platforms
```

## Установка в Linux

1. Установите библиотеки для работы со звуком и для сборки пакетов Python:

   ```
   sudo apt-get install -y python3-dev libasound2-dev
   ```

2. Установите зависимости для Python:

   ```
   bash install_requirements.sh
   ```

Если Вы используете для работы с EPLab Ubuntu 20, необходимо использовать GLIBC версии 2.29. Для работы с Ubuntu 18 используется GLIBC 2.27 и обновление библиотеки не требуется!

Если при установке зависимостей через hg возникает ошибка авторизации, то нужно прописать в Hg логин и пароль от репозитория hg.ximc.ru. Это можно сделать через TortoiseHg, открыв любой репозиторий, перейдя во вкладку синхронизации (две стрелочки по кругу на верхней панели) и нажав на иконку с изображением замка (в середине страницы, слева от строки с адресом сервера). После этого нужно переоткрыть консоль. Также нужен доступ на hg.ximc.ru к репозиториям epcore, ivviewer.

Если у вас возникла такая ошибка:

`qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found`
выполните следующие команды:

```
export QT_DEBUG_PLUGINS=1
sudo apt-get install --reinstall libxcb-xinerama0
```


Если при подключении вахометров они не обнаруживаются, то стоит прописать в системе VID и PID устройства для драйвера виртуального COM-порта. В Ubuntu это можно сделать так:

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

`ivm_url` - это адрес COM-порта. Также `ivm_url` может быть `virtual` (будет использоваться виртуальный измеритель).

Пример запуска:

```
python main.py com:\\.\COM13 --ref virtual
```

Если используется виртуальное окружение, то запускать нужно так:

```
venv\Scripts\python main.py com:\\.\COM13 --ref virtual
```

## Запуск в Linux

```
python3 main.py <ivm_url> [--ref <ivm_url>]
```
ПО может работать как с одним, так и с двумя устройствами (второе устройство задавать не обязательно).

`ivm_url` - это адрес COM-порта. Также `ivm_url` может быть `virtual` (будет использоваться виртуальный измеритель).

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

## Релиз в Windows

Для релиза есть скрипт `release.bat`. В нём нужно прописать путь до системного интерпретатора Python. Для запуска в консоли набрать:

```
release.bat
```
Собранный релиз будет лежать в папке `release`.

## Релиз в Linux

Для выпуска релиза на Linux нужно запустить на исполнение скрипт `release.sh`:

```
bash release.sh
```

Собранный релиз будет лежать в папке `release`.

## Запуск тестов

```
venv\Scripts\python -m unittest discover -s tests -p "test_*.py"
```

## Дополнительно

Файл платы для тестов можно загрузить из папки  `tests\test_data\eyepoint_calibration_board`.

Чтобы сконвертировать файлы плат, сделанные с помощью EyePoint Px, можно воспользоваться конвертером, который находится в модуле `epcore.utils`.

