# Весь код в репозитории сгенерирован с помощью ChatGPT!

В папке backend лежит код на pythob с использованием NiceGUI библиотеки для веб интерфейса.
В папке esp - код для esp8266 с 4 реле

Управление esp происходит по telnet

# Система управления поливом

Программа позволяет управлять системой полива через веб-интерфейс и интегрируется с Home Assistant через MQTT. Она предоставляет возможность контролировать состояние клапанов, настраивать расписание полива и получать актуальную информацию о системе.

## Функциональные возможности

- Управление клапанами: Включение и выключение клапанов через веб-интерфейс.
- Настройка расписания: Создание расписания для автоматического полива в определенные дни и время.
- Интеграция с Home Assistant: Контроль и управление системой полива через Home Assistant с использованием MQTT.
- Отображение состояния: Получение текущего состояния клапанов и отображение их статуса в реальном времени.
- Логирование действий: Ведение журнала всех действий для последующего анализа.

### Как работает программа

- Веб-интерфейс: Пользовательский интерфейс, созданный с помощью библиотеки NiceGUI, предоставляет доступ к управлению клапанами и настройке расписания.
- Связь с устройством: Программа взаимодействует с устройством управления клапанами через сокеты, отправляя команды и получая статус.
- MQTT Интеграция: Состояние клапанов и команды управления передаются через MQTT брокер, что позволяет интегрироваться с Home Assistant.
- Расписание: Используется планировщик задач для автоматического включения и выключения клапанов в заданное время согласно расписанию.
- Конфигурация: Все настройки, включая параметры MQTT и информацию о клапанах, хранятся в файле config.json.

# Watering Control System
The program allows you to manage a watering system through a web interface and integrates with Home Assistant via MQTT. It provides the ability to control valve states, set up watering schedules, and obtain up-to-date information about the system.

## Features

- Valve Control: Turn valves on and off through a web interface.
- Schedule Configuration: Create schedules for automatic watering on specific days and times.
- Home Assistant Integration: Control and manage the watering system through Home Assistant using MQTT.
- Status Display: Obtain the current state of the valves and display their status in real-time.
- Action Logging: Keep a log of all actions for subsequent analysis.

### How the Program Works

- Web Interface: A user interface built with NiceGUI library provides access to valve control and schedule settings.
- Device Communication: The program communicates with the valve control device via sockets, sending commands and receiving status updates.
- MQTT Integration: Valve states and control commands are transmitted through an MQTT broker, allowing integration with Home Assistant.
- Scheduling: A task scheduler is used to automatically turn valves on and off at specified times according to the schedule.
- Configuration: All settings, including MQTT parameters and valve information, are stored in the config.json file.

