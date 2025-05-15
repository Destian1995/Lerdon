from lerdon_libraries import *

from economic import *
import economic
import army
import politic
from ii import AIController
from sov import AdvisorView
from event_manager import EventManager
from results_game import ResultsGame




# === Настройка пути к базе данных ===
if platform == 'android':
    from android.storage import app_storage_path
    storage_dir = app_storage_path()
else:
    storage_dir = os.path.dirname(__file__)

original_db_path = os.path.join(os.path.dirname(__file__), 'game_data.db')
copied_db_path = os.path.join(storage_dir, 'game_data.db')

# Принудительно задаём глобальный db_path
db_path = copied_db_path  # ← Эта строка делает db_path доступным сразу

# Копируем БД, если её нет в пользовательской директории
if not os.path.exists(copied_db_path):
    if os.path.exists(original_db_path):
        import shutil
        shutil.copy(original_db_path, copied_db_path)
        print(f"✅ База данных скопирована в {copied_db_path}")
    else:
        raise FileNotFoundError(f"❌ game_data.db отсутствует в проекте!")

# Новые кастомные виджеты
class ModernButton(Button):
    bg_color = ListProperty([0.11, 0.15, 0.21, 1])


class ResourceCard(BoxLayout):
    text = StringProperty('')
    icon = StringProperty('')
    bg_color = ListProperty([0.16, 0.20, 0.27, 0.9])


def parse_formatted_number(formatted_str):
    """Преобразует отформатированную строку с приставкой обратно в число"""
    # Словарь множителей для приставок
    multipliers = {
        'тыс': 1e3,
        'млн': 1e6,
        'млрд': 1e9,
        'трлн': 1e12,
        'квадр': 1e15,
        'квинт': 1e18,
        'секст': 1e21,
        'септил': 1e24,
        'октил': 1e27,
        'нонил': 1e30,
        'децил': 1e33,
        'андец': 1e36
    }

    try:
        # Удаляем лишние символы и разбиваем на части
        parts = formatted_str.replace(',', '.').replace('.', '', 1).split()
        number_part = parts[0]
        suffix = parts[1].rstrip('.').lower() if len(parts) > 1 else ''

        # Парсим числовую часть
        base_value = float(number_part)

        # Находим соответствующий множитель
        for key in multipliers:
            if suffix.startswith(key.lower()):
                return base_value * multipliers[key]

        return base_value

    except (ValueError, IndexError, AttributeError):
        return float('nan')  # Возвращаем NaN при ошибке парсинга


# Список всех фракций
FACTIONS = ["Аркадия", "Селестия", "Хиперион", "Халидон", "Этерия"]
global_resource_manager = {}
translation_dict = {
    "Аркадия": "arkadia",
    "Селестия": "celestia",
    "Этерия": "eteria",
    "Хиперион": "giperion",
    "Халидон": "halidon",
}


def transform_filename(file_path):
    path_parts = file_path.split('/')
    for i, part in enumerate(path_parts):
        for ru_name, en_name in translation_dict.items():
            if ru_name in part:
                path_parts[i] = part.replace(ru_name, en_name)
    return '/'.join(path_parts)


class GameStateManager:
    def __init__(self):
        self.faction = None  # Объект фракции
        self.resource_box = None  # Объект ResourceBox
        self.game_area = None  # Центральная область игры
        self.conn = None  # Соединение с базой данных
        self.cursor = None  # Курсор для работы с БД
        self.turn_counter = 1  # Счетчик ходов

    def initialize(self, selected_faction, db_path=db_path):
        """Инициализация объектов игры."""
        self.faction = Faction(selected_faction)  # Создаем объект фракции
        self.conn = sqlite3.connect(db_path)  # Подключаемся к базе данных
        self.cursor = self.conn.cursor()
        self.turn_counter = self.load_turn(selected_faction)  # Загружаем счетчик ходов

    def load_turn(self, faction):
        """Загружает текущее значение счетчика ходов из базы данных."""
        try:
            self.cursor.execute('''
                SELECT turn_count
                FROM turn
                WHERE faction = ?
            ''', (faction,))
            row = self.cursor.fetchone()
            return row[0] if row else 1
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке счетчика ходов: {e}")
            return 0

    def save_turn(self, faction, turn_count):
        """Сохраняет текущее значение счетчика ходов в базу данных."""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO turn (faction, turn_count)
                VALUES (?, ?)
            ''', (faction, turn_count))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении счетчика ходов: {e}")

    def close_connection(self):
        """Закрывает соединение с базой данных."""
        if self.conn:
            self.conn.close()


class ResourceBox(BoxLayout):
    def __init__(self, resource_manager, **kwargs):
        super(ResourceBox, self).__init__(**kwargs)
        self.resource_manager = resource_manager
        self.orientation = 'vertical'
        self.spacing = dp(5)
        self.padding = [dp(15), dp(25), dp(15), dp(25)]
        # дефолтные size/pos — будут переопределены ниже
        self.pos_hint = {'x': 0, 'top': 1}

        # узнаём, мобильная ли платформа
        app = App.get_running_app()
        is_mobile = getattr(app, 'is_mobile', False)

        # текущие размеры окна
        width, height = Window.size
        is_landscape = width > height

        # адаптивный size_hint
        if is_mobile:
            if is_landscape:
                self.size_hint = (0.45, 0.3)
            else:
                self.size_hint = (0.35, 0.4)
        else:
            if width >= 1200:
                self.size_hint = (0.2, 0.3)
            elif width >= 800:
                self.size_hint = (0.25, 0.35)
            else:
                self.size_hint = (0.3, 0.4)

        # фон с закруглёнными углами
        with self.canvas.before:
            Color(0.11, 0.15, 0.21, 0.9)
            self.rect = RoundedRectangle(radius=[25])

        # чтобы фон перемещался/масштабировался вместе с виджетом
        self.bind(pos=self._update_rect, size=self._update_rect)

        # ваши лейблы и начальная инициализация
        self.labels = {}
        self.update_resources()
        self.bind(size=self.update_font_sizes)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def update_resources(self):
        resources = self.resource_manager.get_resources()

        # Парсим все значения заранее для удобства сравнения
        parsed_values = {}
        for name, value in resources.items():
            parsed_values[name] = parse_formatted_number(value)

        self.clear_widgets()
        self.labels.clear()

        for resource_name, formatted_value in resources.items():
            try:
                numeric_value = parsed_values[resource_name]

                # Проверяем для "Потребление" и "Лимит армии"
                if resource_name == "Потребление":
                    limit_army = parsed_values.get("Лимит армии", 0)
                    if numeric_value > limit_army:
                        text_color = (1, 0, 0, 1)  # Красный
                    else:
                        text_color = (1, 1, 1, 1)  # Белый
                else:
                    # Стандартная проверка на отрицательные значения
                    if numeric_value < 0:
                        text_color = (1, 0, 0, 1)  # Красный
                    else:
                        text_color = (1, 1, 1, 1)  # Белый

                display_value = formatted_value

            except (TypeError, ValueError, KeyError):
                # Обработка ошибок парсинга или отсутствия ключа
                text_color = (1, 1, 1, 1)
                display_value = formatted_value

            # Создаем и настраиваем Label
            label = Label(
                text=f"{resource_name}: {display_value}",
                size_hint_y=None,
                height=self.calculate_label_height(),
                font_size=self.calculate_font_size(),
                color=text_color,
                bold=True,
                markup=True
            )
            self.labels[resource_name] = label
            self.add_widget(label)

    def calculate_font_size(self):
        # Увеличиваем базовый размер для Android
        if platform == 'android':
            base_font_size = sp(14)
            min_size = sp(9)
        else:
            base_font_size = sp(20)
            min_size = sp(12)

        scale_factor = min(self.height / 800, self.width / 600)
        return max(base_font_size * scale_factor, min_size)

    def calculate_label_height(self):
        return self.calculate_font_size() * 2.2

    def update_font_sizes(self, *args):
        new_font_size = self.calculate_font_size()
        for label in self.labels.values():
            label.font_size = new_font_size
            label.height = self.calculate_label_height()


# Класс для кнопки с изображением
class ImageButton(ButtonBehavior, Image):
    pass


class GameScreen(Screen):
    def __init__(self, selected_faction, cities, db_path=None, **kwargs):
        super(GameScreen, self).__init__(**kwargs)
        self.selected_faction = selected_faction
        self.cities = cities
        self.db_path = db_path or 'game_data.db'
        # Инициализация GameStateManager
        self.game_state_manager = GameStateManager()
        self.game_state_manager.initialize(selected_faction)
        # Доступ к объектам через менеджер состояния
        self.faction = self.game_state_manager.faction
        self.conn = self.game_state_manager.conn
        self.cursor = self.game_state_manager.cursor
        self.turn_counter = self.game_state_manager.turn_counter

        # Сохраняем текущую фракцию игрока
        self.save_selected_faction_to_db()
        # Инициализация политических данных
        self.initialize_political_data()
        # Инициализация AI-контроллеров
        self.ai_controllers = {}
        # Инициализация EventManager
        self.event_manager = EventManager(self.selected_faction, self, self.game_state_manager.faction)
        # Инициализация UI
        self.is_android = platform == 'android'
        self.init_ui()
        # Запускаем обновление ресурсов каждую 1 секунду
        Clock.schedule_interval(self.update_cash, 1)

    def init_ui(self):
        # === Контейнер для кнопки "Завершить ход" ===
        end_turn_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(150), dp(60)),
            pos_hint={'x': 0, 'y': 0.23},
            padding=dp(5)
        )
        with end_turn_container.canvas.before:
            Color(1, 0.2, 0.2, 0.9)  # Цвет фона кнопки
            RoundedRectangle(pos=end_turn_container.pos, size=end_turn_container.size, radius=[15])

        def update_end_turn_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(1, 0.2, 0.2, 0.9)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[15])

        end_turn_container.bind(pos=update_end_turn_rect, size=update_end_turn_rect)

        # === Сама кнопка внутри контейнера ===
        self.end_turn_button = Button(
            text="Завершить ход",
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0),  # Отключаем стандартный фон кнопки
            font_size=sp(20),
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.end_turn_button.bind(on_press=self.process_turn)
        end_turn_container.add_widget(self.end_turn_button)

        self.add_widget(end_turn_container)

        # === Контейнер для названия фракции ===
        fraction_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(130) if self.is_android else 150, dp(40) if self.is_android else 40),
            pos_hint={'x': 0.25, 'top': 1},  # Левее кнопки выхода и ближе к потолку
            padding=dp(10)
        )
        with fraction_container.canvas.before:
            Color(0.15, 0.2, 0.3, 0.95)
            self.fraction_rect = RoundedRectangle(radius=[15])

        def update_fraction_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.15, 0.2, 0.3, 0.95)
                self.fraction_rect = RoundedRectangle(pos=instance.pos, size=instance.size, radius=[15])

        fraction_container.bind(pos=update_fraction_rect, size=update_fraction_rect)
        self.faction_label = Label(
            text=f"{self.selected_faction}",
            font_size=sp(20) if self.is_android else '24sp',
            bold=True,
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        self.faction_label.bind(size=self.faction_label.setter('text_size'))
        fraction_container.add_widget(self.faction_label)
        self.add_widget(fraction_container)

        # === Боковая панель с кнопками режимов ===
        mode_panel_width = dp(80)
        mode_panel_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, 0.7),
            width=mode_panel_width,
            pos_hint={'right': 1, 'top': 0.86},
            padding=dp(10),
            spacing=dp(10)
        )
        with mode_panel_container.canvas.before:
            Color(0.15, 0.2, 0.3, 0.9)
            RoundedRectangle(pos=mode_panel_container.pos, size=mode_panel_container.size, radius=[15])

        def update_mode_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.15, 0.2, 0.3, 0.9)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[15])

        mode_panel_container.bind(pos=update_mode_rect, size=update_mode_rect)
        btn_advisor = ImageButton(source=transform_filename(f'files/sov/sov_{self.selected_faction}.jpg'),
                                  size_hint=(1, None), height=dp(60), on_press=self.show_advisor)
        btn_economy = ImageButton(source='files/status/economy.png', size_hint=(1, None), height=dp(60),
                                  on_press=self.switch_to_economy)
        btn_army = ImageButton(source='files/status/army.png', size_hint=(1, None), height=dp(60),
                               on_press=self.switch_to_army)
        btn_politics = ImageButton(source='files/status/politic.png', size_hint=(1, None), height=dp(60),
                                   on_press=self.switch_to_politics)
        mode_panel_container.add_widget(btn_advisor)
        mode_panel_container.add_widget(btn_economy)
        mode_panel_container.add_widget(btn_army)
        mode_panel_container.add_widget(btn_politics)
        self.add_widget(mode_panel_container)

        # === Центральная область ===
        self.game_area = FloatLayout(size_hint=(0.7, 1), pos_hint={'x': 0.25, 'y': 0})
        self.add_widget(self.game_area)

        # === Счётчик ходов ===
        turn_counter_size = (dp(200), dp(50))
        turn_counter_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=turn_counter_size,
            pos_hint={'right': 0.7, 'top': 1},
            padding=dp(10),
            spacing=dp(5)
        )
        with turn_counter_container.canvas.before:
            Color(0.15, 0.2, 0.3, 0.9)
            RoundedRectangle(pos=turn_counter_container.pos, size=turn_counter_container.size, radius=[15])

        def update_turn_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.15, 0.2, 0.3, 0.9)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[15])

        turn_counter_container.bind(pos=update_turn_rect, size=update_turn_rect)
        self.turn_label = Label(text=f"Текущий ход: {self.turn_counter}", font_size='18sp', color=(1, 1, 1, 1),
                                bold=True, halign='center')
        turn_counter_container.add_widget(self.turn_label)
        self.add_widget(turn_counter_container)


        # === Контейнер для кнопки выхода ===
        exit_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(120) if self.is_android else 120, dp(60) if self.is_android else 60),
            pos_hint={'x': 0.85, 'y': 0},
            padding=dp(10),
            spacing=dp(5)
        )
        with exit_container.canvas.before:
            Color(0.1, 0.5, 0.1, 1)
            RoundedRectangle(pos=exit_container.pos, size=exit_container.size, radius=[15])

        def update_exit_rect(instance, value):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.15, 0.2, 0.3, 0.9)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[15])

        exit_container.bind(pos=update_exit_rect, size=update_exit_rect)
        self.exit_button = Button(
            text="Выход",
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0),
            font_size='16sp',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.exit_button.bind(on_press=lambda x: self.confirm_exit())
        exit_container.add_widget(self.exit_button)
        self.add_widget(exit_container)
        # === ResourceBox ===
        self.resource_box = ResourceBox(resource_manager=self.faction)
        self.resource_box.size_hint = (0.2, 0.7)
        self.resource_box.pos_hint = {'x': 0, 'y': 0.4}
        Window.bind(on_resize=self.on_window_resize)
        self.add_widget(self.resource_box)

        # === Инициализация ИИ ===
        self.init_ai_controllers()

    def on_window_resize(self, instance, width, height):
        is_landscape = width > height
        if is_landscape:
            self.resource_box.size_hint = (0.2, 0.9)
            self.resource_box.pos_hint = {'x': 0, 'y': 0}
            self.game_area.size_hint = (0.6, 1)
            self.game_area.pos_hint = {'x': 0.2, 'y': 0}
            self.end_turn_button.pos_hint = {'x': 0.02, 'y': 0.02}
            self.turn_label.text = f"Ход: {self.turn_counter}"
        else:
            self.resource_box.size_hint = (0.25, 0.95)
            self.resource_box.pos_hint = {'x': 0, 'y': 0}
            self.game_area.size_hint = (0.7, 1)
            self.game_area.pos_hint = {'x': 0.25, 'y': 0}
            self.end_turn_button.pos_hint = {'x': 0.02, 'y': 0.02}

    def save_selected_faction_to_db(self):
        """
        Сохраняет выбранную фракцию пользователя в таблицу user_faction.
        """
        try:
            # SQL-запрос для вставки данных
            query = "INSERT INTO user_faction (faction) VALUES (?)"
            # Выполнение запроса с кортежем в качестве параметра
            self.cursor.execute(query, (self.selected_faction,))
            # Фиксация изменений в базе данных
            self.conn.commit()
            print(f"Фракция '{self.selected_faction}' успешно сохранена для пользователя.")
        except Exception as e:
            # Откат изменений в случае ошибки
            self.conn.rollback()
            print(f"Ошибка при сохранении фракции: {e}")

    def process_turn(self, instance=None):
        """
        Обработка хода игрока и ИИ.
        """
        # Увеличиваем счетчик ходов
        self.turn_counter += 1

        # Обновляем метку с текущим ходом
        self.turn_label.text = f"Текущий ход: {self.turn_counter}"

        # Сохраняем текущее значение хода в таблицу turn
        self.save_turn(self.selected_faction, self.turn_counter)
        # Сохраняем историю ходов в таблицу turn_save
        self.save_turn_history(self.selected_faction, self.turn_counter)

        # Обновляем ресурсы игрока
        self.faction.update_resources()
        self.resource_box.update_resources()

        # Проверяем условие завершения игры
        game_continues, reason = self.faction.end_game()  # Получаем статус и причину завершения
        if not game_continues:
            print("Условия завершения игры выполнены.")

            # Определяем статус завершения (win или lose)
            if "Мир во всем мире" in reason or "Все фракции были уничтожены" in reason:
                status = "win"  # Условия победы
            else:
                status = "lose"  # Условия поражения
            # Запускаем модуль results_game для обработки результатов
            results_game_instance = ResultsGame(status, reason)  # Создаем экземпляр класса ResultsGame
            results_game_instance.show_results(self.selected_faction, status, reason)
            App.get_running_app().restart_app()  # Добавляем прямой вызов перезагрузки
            return  # Прерываем выполнение дальнейших действий

        # Выполнение хода для всех ИИ
        for ai_controller in self.ai_controllers.values():
            ai_controller.make_turn()

        # Обновляем статус уничтоженных фракций
        self.update_destroyed_factions()
        # Обновляем статус ходов
        self.reset_check_attack_flags()
        self.initialize_turn_check_move()
        # Логирование или обновление интерфейса после хода
        print(f"Ход {self.turn_counter} завершён")

        self.event_now = random.randint(9, 10)
        # Проверяем, нужно ли запустить событие
        if self.turn_counter % self.event_now == 0:
            print("Генерация события...")
            self.event_manager.generate_event(self.turn_counter)

    def confirm_exit(self):
        # Создаем контент попапа
        content = BoxLayout(orientation='vertical', spacing=10)
        message = Label(text="Вы точно хотите выйти?")
        btn_yes = Button(text="Да", size_hint=(1, 0.4))
        btn_no = Button(text="Нет", size_hint=(1, 0.4))

        # Создаем попап
        popup = Popup(
            title="Подтверждение выхода",
            content=content,
            size_hint=(0.5, 0.4)
        )

        # Назначаем действия кнопкам
        btn_yes.bind(on_press=lambda x: (popup.dismiss(), App.get_running_app().restart_app()))
        btn_no.bind(on_press=popup.dismiss)

        content.add_widget(message)
        content.add_widget(btn_yes)
        content.add_widget(btn_no)
        popup.open()

    def initialize_political_data(self):
        """
        Инициализирует таблицу political_systems значениями по умолчанию,
        если она пуста. Политическая система для каждой фракции выбирается случайным образом.
        Условие: не может быть меньше 2 и больше 3 стран с одним политическим строем.
        """
        try:
            # Проверяем, есть ли записи в таблице
            self.cursor.execute("SELECT COUNT(*) FROM political_systems")
            count = self.cursor.fetchone()[0]
            if count == 0:
                # Список всех фракций
                factions = ["Аркадия", "Селестия", "Хиперион", "Этерия", "Халидон"]

                # Список возможных политических систем
                systems = ["Капитализм", "Коммунизм"]

                # Функция для проверки распределения
                def is_valid_distribution(distribution):
                    counts = {system: distribution.count(system) for system in systems}
                    return all(2 <= count <= 3 for count in counts.values())

                # Генерация случайного распределения
                while True:
                    default_systems = [(faction, random.choice(systems)) for faction in factions]
                    distribution = [system for _, system in default_systems]

                    if is_valid_distribution(distribution):
                        break

                # Вставляем данные в таблицу
                self.cursor.executemany(
                    "INSERT INTO political_systems (faction, system) VALUES (?, ?)",
                    default_systems
                )
                self.conn.commit()
                print("Таблица political_systems инициализирована случайными значениями.")
        except sqlite3.Error as e:
            print(f"Ошибка при инициализации таблицы political_systems: {e}")

    def update_cash(self, dt):
        """Обновление текущего капитала фракции через каждые 1 секунду."""
        self.faction.update_cash()
        self.resource_box.update_resources()

    def switch_to_economy(self, instance):
        """Переключение на экономическую вкладку."""
        self.clear_game_area()
        economic.start_economy_mode(self.game_state_manager.faction, self.game_area)

    def switch_to_army(self, instance):
        """Переключение на армейскую вкладку."""
        self.clear_game_area()
        army.start_army_mode(self.selected_faction, self.game_area, self.game_state_manager.faction)

    def switch_to_politics(self, instance):
        """Переключение на политическую вкладку."""
        self.clear_game_area()
        politic.start_politic_mode(self.selected_faction, self.game_area, self.game_state_manager.faction)

    def clear_game_area(self):
        """Очистка центральной области."""
        self.game_area.clear_widgets()

    def on_stop(self):
        """Закрытие соединения с базой данных при завершении игры."""
        self.game_state_manager.close_connection()

    def show_advisor(self, instance):
        """Показать экран советника"""
        self.clear_game_area()
        advisor_view = AdvisorView(self.selected_faction)
        self.game_area.add_widget(advisor_view)

    def update_destroyed_factions(self):
        """
        Обновляет статус фракций в таблице diplomacies.
        Если у фракции нет ни одного города в таблице city,
        все записи для этой фракции в таблице diplomacies помечаются как "уничтожена".
        """
        try:
            # Шаг 1: Получаем список всех фракций, у которых есть города
            self.cursor.execute("""
                SELECT DISTINCT kingdom
                FROM city
            """)
            factions_with_cities = {row[0] for row in self.cursor.fetchall()}

            # Шаг 2: Получаем все уникальные фракции из таблицы diplomacies
            self.cursor.execute("""
                SELECT DISTINCT faction1
                FROM diplomacies
            """)
            all_factions = {row[0] for row in self.cursor.fetchall()}

            # Шаг 3: Определяем фракции, у которых нет ни одного города
            destroyed_factions = all_factions - factions_with_cities

            if destroyed_factions:
                print(f"Фракции без городов (уничтожены): {', '.join(destroyed_factions)}")

                # Шаг 4: Обновляем записи в таблице diplomacies для уничтоженных фракций
                for faction in destroyed_factions:
                    self.cursor.execute("""
                        UPDATE diplomacies
                        SET relationship = ?
                        WHERE faction1 = ? OR faction2 = ?
                    """, ("уничтожена", faction, faction))
                    print(f"Статус фракции '{faction}' обновлен на 'уничтожена'.")

                # Фиксируем изменения в базе данных
                self.conn.commit()
            else:
                print("Все фракции имеют хотя бы один город. Нет уничтоженных фракций.")

        except sqlite3.Error as e:
            print(f"Ошибка при обновлении статуса уничтоженных фракций: {e}")

    def reset_check_attack_flags(self):
        """
        Обновляет значения check_attack на False для всех записей в таблице turn_check_attack_faction.
        """
        try:
            self.cursor.execute("""
                UPDATE turn_check_attack_faction
                SET check_attack = ?
            """, (False,))
            self.conn.commit()
            print("Флаги check_attack успешно сброшены на False.")
        except sqlite3.Error as e:
            print(f"Ошибка при сбросе флагов check_attack: {e}")

    def initialize_turn_check_move(self):
        """
        Инициализирует запись о возможности перемещения для текущей фракции.
        Устанавливает значение 'can_move' = True по умолчанию.
        """

        try:
            self.cursor.execute("""
                UPDATE turn_check_move
                SET can_move = ?
            """, (True,))
            self.conn.commit()
            print("Флаги can_move успешно сброшены на True.")
        except sqlite3.Error as e:
            print(f"Ошибка при сбросе флагов can_move: {e}")

    def init_ai_controllers(self):
        """Создание контроллеров ИИ для каждой фракции кроме выбранной"""
        for faction in FACTIONS:
            if faction != self.selected_faction:
                self.ai_controllers[faction] = AIController(faction)

    def load_turn(self, faction):
        """Загрузка текущего значения хода для фракции."""
        self.cursor.execute('SELECT turn_count FROM turn WHERE faction = ?', (faction,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def save_turn(self, faction, turn_count):
        """Сохранение текущего значения хода для фракции."""
        self.cursor.execute('''
            INSERT OR REPLACE INTO turn (faction, turn_count)
            VALUES (?, ?)
        ''', (faction, turn_count))
        self.conn.commit()

    def save_turn_history(self, faction, turn_count):
        """Сохранение истории ходов в таблицу turn_save."""
        self.cursor.execute('''
            INSERT INTO turn_save (faction, turn_count)
            VALUES (?, ?)
        ''', (faction, turn_count))
        self.conn.commit()

    def reset_game(self):
        """Сброс игры (например, при новой игре)."""
        self.save_turn(self.selected_faction, 0)  # Сбрасываем счетчик ходов до 0
        self.turn_counter = 0
        print("Счетчик ходов сброшен.")