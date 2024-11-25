from nicegui import ui, app
import socket
import json
from datetime import datetime, timedelta
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("watering_log_2024.log", encoding="utf-8")
    ]
)

# Путь к файлу конфигурации
CONFIG_FILE = 'config.json'
STATE_FILE = 'state.json'

# Загрузка конфигурации из файла
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    # Если файла нет, создаем конфигурацию по умолчанию
    config = {
        "device_ip": "192.168.1.48",
        "device_port": 8080,
        "valve_mapping": {1: 16, 2: 14, 3: 12, 4: 13},
        "valve_names": {1: "Клапан 1", 2: "Клапан 2", 3: "Клапан 3", 4: "Клапан 4"},
        "schedule": []
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

DEVICE_IP = config.get('device_ip')
DEVICE_PORT = config.get('device_port')
VALVE_MAPPING = {int(k): v for k, v in config.get('valve_mapping', {}).items()}
VALVE_NAMES = {int(k): v for k, v in config.get('valve_names', {}).items()}
schedule = config.get('schedule', [])

# Соответствие дня недели числу (Понедельник=0)
days_mapping = {
    'Понедельник': 0, 'Вторник': 1, 'Среда': 2, 'Четверг': 3,
    'Пятница': 4, 'Суббота': 5, 'Воскресенье': 6,
}

# Загрузка состояния из файла
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        state = json.load(f)
else:
    state = {}

today_watering_canceled = state.get('today_watering_canceled', False)
canceled_date = state.get('canceled_date', None)

scheduler = AsyncIOScheduler()

@app.on_startup
async def init_scheduler():
    scheduler.start()
    reschedule_jobs()

def log_action(action_type, valves):
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'action': action_type,
        'valves': valves
    }
    logging.info(f"{action_type} - Клапаны: {valves}")
    with open("action_log.json", "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def send_command(action, valves):
    remapped_valves = [str(VALVE_MAPPING.get(valve, valve)) for valve in valves]
    data = f"{action} {','.join(remapped_valves)}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((DEVICE_IP, DEVICE_PORT))
            s.sendall(data.encode())
            logging.info(f"Команда отправлена: {data}")
            if action != 'status':
                log_action(action, valves)
            else:
                response = s.recv(1024).decode()
                return response
    except Exception as e:
        logging.error(f"Ошибка при отправке команды: {e}")
        return None

def get_valve_status():
    response = send_command('status', [])
    valve_status = {}
    if response:
        # Пример ответа: "12=0;13=0;14=0;16=0;"
        status_entries = response.strip().split(';')
        for entry in status_entries:
            if '=' in entry:
                device_valve_number, state = entry.split('=')
                try:
                    device_valve_number = int(device_valve_number)
                    state = int(state)
                    # Найдем логический номер клапана по номеру устройства
                    for valve_number, device_number in VALVE_MAPPING.items():
                        if device_number == device_valve_number:
                            valve_status[valve_number] = bool(state)
                            break
                except ValueError:
                    continue
    return valve_status

def save_config():
    config['schedule'] = schedule
    config['valve_mapping'] = VALVE_MAPPING
    config['valve_names'] = VALVE_NAMES
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def save_state():
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

def reschedule_jobs():
    scheduler.remove_all_jobs()
    today = datetime.now().date()

    for entry in schedule:
        day = entry['day']
        time_str = entry['time']
        duration = entry['duration']
        valves = entry['valves']
        hour, minute = map(int, time_str.split(':'))

        day_of_week = days_mapping.get(day, None)
        if day_of_week is None:
            logging.warning(f"Некорректный день недели: {day}")
            continue

        skip_today = False
        if today_watering_canceled and canceled_date == today.isoformat():
            if today.weekday() == day_of_week:
                skip_today = True

        if skip_today:
            continue

        trigger_on = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        scheduler.add_job(send_command, trigger=trigger_on, args=['on', valves])

        start_time = datetime.strptime(time_str, '%H:%M')
        off_time = (start_time + timedelta(minutes=int(duration))).time()
        hour_off = off_time.hour
        minute_off = off_time.minute

        trigger_off = CronTrigger(day_of_week=day_of_week, hour=hour_off, minute=minute_off)
        scheduler.add_job(send_command, trigger=trigger_off, args=['off', valves])

def get_last_actions():
    try:
        with open("action_log.json", "r", encoding="utf-8") as log_file:
            logs = [json.loads(line) for line in log_file.readlines()]
            return logs[-30:]
    except FileNotFoundError:
        return []

def main_page():
    global cancel_button, today_watering_canceled, canceled_date, schedule_container, valve_states, valve_switches_container

    with ui.header().classes('items-center justify-center') as header:
        ui.label('Система управления поливом - 2024').classes('text-h4 text-white')
        header.props('elevated')
        header.style('background-color: #4CAF50;')

    def show_last_actions():
        last_actions = get_last_actions()
        with ui.dialog() as dialog:
            with ui.card().style('width: 600px;'):
                ui.label('Последние действия').classes('text-h6')
                with ui.element('table').style('width: 100%; border-collapse: collapse;'):
                    with ui.element('thead'):
                        with ui.element('tr'):
                            for header_text in ['Время', 'Действие', 'Клапаны']:
                                with ui.element('th').style('border: 1px solid black; padding: 5px;'):
                                    ui.label(header_text)
                    with ui.element('tbody'):
                        for log in last_actions:
                            with ui.element('tr'):
                                timestamp = datetime.fromisoformat(log['timestamp']).strftime('%d.%m.%Y %H:%M')
                                action = 'Включение' if log['action'] == 'on' else 'Выключение'
                                valves = ', '.join(VALVE_NAMES.get(v, f'Клапан {v}') for v in log['valves'])
                                for value in [timestamp, action, valves]:
                                    with ui.element('td').style('border: 1px solid black; padding: 5px;'):
                                        ui.label(value)
                ui.button('Закрыть', on_click=dialog.close, color='grey', icon='close')
        dialog.open()

    def show_settings():
        with ui.dialog() as dialog:
            with ui.card().style('width: 600px;'):
                ui.label('Настройки клапанов').classes('text-h6')
                valve_entries = []
                with ui.element('table').style('width: 100%; border-collapse: collapse;'):
                    with ui.element('thead'):
                        with ui.element('tr'):
                            for header_text in ['Номер', 'Номер на устройстве', 'Имя']:
                                with ui.element('th').style('border: 1px solid black; padding: 5px;'):
                                    ui.label(header_text)
                    with ui.element('tbody'):
                        for valve_number in sorted(VALVE_NAMES.keys()):
                            valve_name = VALVE_NAMES[valve_number]
                            device_valve_number = VALVE_MAPPING.get(valve_number, valve_number)
                            with ui.element('tr'):
                                with ui.element('td').style('border: 1px solid black; padding: 5px;'):
                                    ui.label(f'{valve_number}')
                                with ui.element('td').style('border: 1px solid black; padding: 5px;'):
                                    device_input = ui.input(value=str(device_valve_number)).props('type=number').classes('w-full')
                                with ui.element('td').style('border: 1px solid black; padding: 5px;'):
                                    name_input = ui.input(value=valve_name).classes('w-full')
                                valve_entries.append((valve_number, device_input, name_input))

                def save_settings():
                    global VALVE_MAPPING, VALVE_NAMES
                    for valve_number, device_input, name_input in valve_entries:
                        try:
                            device_valve_number = int(device_input.value)
                            VALVE_MAPPING[valve_number] = device_valve_number
                        except ValueError:
                            pass  # ignore invalid number
                        VALVE_NAMES[valve_number] = name_input.value
                    save_config()
                    update_valve_switches()
                    dialog.close()

                with ui.row().classes('justify-end'):
                    ui.button('Сохранить', on_click=save_settings, color='green', icon='check')
                    ui.button('Отмена', on_click=dialog.close, color='grey', icon='close')
        dialog.open()

    def update_valve_switches():
        build_valve_switches()
        refresh_schedule()

    # Получаем состояние клапанов при загрузке страницы
    initial_valve_status = get_valve_status()

    with ui.element('div').style('display: flex; width: 100%; padding: 20px;'):
        with ui.card().style('flex: 0 0 40%; margin-right: 10px;'):
            with ui.row().classes('items-center justify-between'):
                ui.label('Управление кранами').classes('text-h5')
                with ui.row().classes('items-center'):
                    ui.button('', on_click=show_settings, icon='settings', color='primary')
                    ui.button('', on_click=show_last_actions, icon='history', color='primary')
            valve_states = {}
            valve_switches_container = ui.column()

            def create_valve_switch(valve_number):
                def on_change(e):
                    action = 'on' if e.value else 'off'
                    send_command(action, [valve_number])

                valve_name = VALVE_NAMES.get(valve_number, f'Клапан {valve_number}')
                switch = ui.switch(valve_name, on_change=on_change)
                # Устанавливаем начальное состояние переключателя
                if initial_valve_status and valve_number in initial_valve_status:
                    switch.value = initial_valve_status[valve_number]
                valve_states[valve_number] = switch

            def build_valve_switches():
                valve_switches_container.clear()
                with valve_switches_container:
                    for valve_number in VALVE_NAMES.keys():
                        create_valve_switch(valve_number)

            build_valve_switches()

            def close_all_valves():
                send_command('off', list(VALVE_NAMES.keys()))
                for switch in valve_states.values():
                    switch.value = False

            ui.button('Закрыть все краны', on_click=close_all_valves, color='red', icon='close')

        with ui.card().style('flex: 1; margin-left: 10px;'):
            ui.label('Управление расписанием').classes('text-h5')
            schedule_container = ui.column().classes('w-full')

            def refresh_schedule():
                schedule_container.clear()

                def sort_key(entry):
                    day_num = days_mapping.get(entry['day'], 7)
                    time_obj = datetime.strptime(entry['time'], '%H:%M')
                    return (day_num, time_obj)

                indexed_schedule = [{'idx': idx, 'entry': entry} for idx, entry in enumerate(schedule)]
                sorted_schedule = sorted(indexed_schedule, key=lambda x: sort_key(x['entry']))

                with schedule_container:
                    with ui.element('table').classes('schedule-table').style('width: 100%; border-collapse: collapse;'):
                        with ui.element('thead'):
                            with ui.element('tr'):
                                for header_text in ['День недели', 'Время', 'Длительность (мин)', 'Клапаны', 'Действия']:
                                    with ui.element('th').style('border: 1px solid black; padding: 5px;'):
                                        ui.label(header_text)
                        with ui.element('tbody'):
                            for item in sorted_schedule:
                                idx = item['idx']
                                entry = item['entry']
                                valves_display = ', '.join(VALVE_NAMES.get(v, f'Клапан {v}') for v in entry['valves'])
                                with ui.element('tr'):
                                    for value in [entry['day'], entry['time'], entry['duration'], valves_display]:
                                        with ui.element('td').style('border: 1px solid black; padding: 5px;'):
                                            ui.label(str(value))
                                    with ui.element('td').style('border: 1px solid black; padding: 5px;'):
                                        ui.button('Удалить', on_click=lambda _, idx=idx: delete_schedule_entry(idx), color='red', icon='delete')

                update_cancel_button_state()

            def delete_schedule_entry(idx):
                schedule.pop(idx)
                save_config()
                refresh_schedule()
                reschedule_jobs()

            def add_schedule_entry():
                with ui.dialog() as dialog:
                    with ui.card():
                        ui.label('Добавить в расписание').classes('text-h6')
                        with ui.column():
                            day_of_week = ui.select(
                                ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'],
                                label='Выберите день недели',
                                value='Понедельник'
                            ).classes('w-full')
                            time_input = ui.input(label='Время').props('type=time').classes('w-full')
                            duration_input = ui.number(label='Длительность (мин)', value=10).classes('w-full')

                            valves_input = ui.select(options=VALVE_NAMES, label='Выберите краны', multiple=True).classes('w-full')

                            def save_entry():
                                try:
                                    if not valves_input.value:
                                        ui.notify('Пожалуйста, выберите хотя бы один кран.', color='red')
                                        return
                                    selected_valves = [int(v) for v in valves_input.value]
                                    new_entry = {
                                        'day': day_of_week.value,
                                        'time': time_input.value,
                                        'duration': duration_input.value,
                                        'valves': selected_valves,
                                    }
                                    schedule.append(new_entry)
                                    save_config()
                                    refresh_schedule()
                                    reschedule_jobs()
                                    dialog.close()
                                except Exception as e:
                                    logging.error(f"Ошибка при сохранении записи расписания: {e}")
                                    ui.notify(f"Ошибка: {e}", color='red')

                            with ui.row().classes('justify-end'):
                                ui.button('Сохранить', on_click=save_entry, color='green', icon='check')
                                ui.button('Отмена', on_click=dialog.close, color='grey', icon='close')
                dialog.open()

            def update_cancel_button_state():
                today = datetime.now().date()
                has_scheduled_today = any(
                    days_mapping.get(entry['day']) == today.weekday() for entry in schedule
                )

                if not has_scheduled_today:
                    cancel_button.disable()
                else:
                    cancel_button.enable()

                if today_watering_canceled and canceled_date == today.isoformat():
                    cancel_button.text = 'Включить сегодняшний полив'
                    color = 'green'
                    icon = 'check_circle'
                else:
                    cancel_button.text = 'Отменить сегодняшний полив'
                    color = 'red'
                    icon = 'cancel'

                cancel_button.props(f'color={color} icon={icon}')
                cancel_button.update()

            def toggle_today_watering():
                global today_watering_canceled, canceled_date
                today = datetime.now().date()
                if today_watering_canceled and canceled_date == today.isoformat():
                    today_watering_canceled = False
                    state['today_watering_canceled'] = False
                    state['canceled_date'] = None
                else:
                    today_watering_canceled = True
                    state['today_watering_canceled'] = True
                    state['canceled_date'] = today.isoformat()
                save_state()
                reschedule_jobs()
                update_cancel_button_state()

            with ui.row().classes('justify-start'):
                ui.button('Добавить в расписание', on_click=add_schedule_entry, icon='add', color='primary')
                cancel_button = ui.button('Отменить сегодняшний полив', on_click=toggle_today_watering)

            refresh_schedule()

    with ui.footer().style('background-color: #4CAF50; color: white;').classes('items-center justify-center'):
        ui.label('© 2024 Система управления поливом')

main_page()

ui.run()
