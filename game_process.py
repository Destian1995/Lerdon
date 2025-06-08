from lerdon_libraries import *
from db_lerdon_connect import *

from economic import *
import economic
import army
import politic
from ii import AIController
from sov import AdvisorView
from event_manager import EventManager
from results_game import ResultsGame
from seasons import SeasonManager


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
    """
    ResourceBox, «приклеенный» к левому верхнему углу,
    с каждой строкой:
      ----------
      [иконка] : [значение]   (шрифт sp(16), иконка dp(16))
      ----------
    Ширина контейнера = dp(72). Текст и иконки не уменьшаются.
    """
    ICON_MAP = {
        "Кроны":      "files/status/resource_box/coin.png",
        "Рабочие":     "files/status/resource_box/workers.png",
        "Сырье":       "files/status/resource_box/surie.png",
        "Население":   "files/status/resource_box/population.png",
        "Потребление": "files/status/resource_box/consumption.png",
        "Лимит армии": "files/status/resource_box/army_limit.png",
    }

    def __init__(self, resource_manager, **kwargs):
        super(ResourceBox, self).__init__(**kwargs)
        self.resource_manager = resource_manager

        # верт. бокс
        self.orientation = 'vertical'

        # фиксированная узкая ширина, привязка к левому верху
        self.size_hint = (None, None)
        self.pos_hint = {'x': 0, 'top': 1}
        self.width = dp(150)  # сокращённая ширина

        # Отступы внутри: [left, top, right, bottom]
        self.padding = [dp(2), dp(2), dp(2), dp(2)]
        # spacing = 0, поскольку сами рисуем разделители
        self.spacing = 0

        # фон с закруглёнными углами
        with self.canvas.before:
            Color(0.11, 0.15, 0.21, 0.9)
            self._bg_rect = RoundedRectangle(radius=[6,])

        self.bind(pos=self._update_bg, size=self._update_bg)

        # Словарь, чтобы хранить метки значений (обновлять при tick)
        self._label_values = {}

        # Сразу строим содержимое
        self.update_resources()

        # При изменении высоты/ширины пересобираем (нужно для корректного рисования линий)
        self.bind(size=lambda *a: self.update_resources())

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def update_resources(self):
        self.clear_widgets()
        self._label_values.clear()

        resources = self.resource_manager.get_resources()
        parsed = {}
        for name, val in resources.items():
            try:
                parsed[name] = parse_formatted_number(val)
            except Exception:
                parsed[name] = None

        row_h = dp(32)
        icon_size = dp(24)
        colon_w = dp(6)
        gap = dp(8)
        val_w = self.width - (self.padding[0] + self.padding[2] + icon_size + gap + colon_w + dp(4))

        widgets = []

        def show_tooltip(res_name):
            info_text = {
                "Кроны": (
                    "Кроны — валюта Лэрдона.\n"
                    "Основной источник: налоги.\n"
                    "Можно получить: продав Сырьё на рынке или от дружественных стран при торговле."
                ),
                "Рабочие": (
                    "Работоспособное население,\nспособное работать на фабриках или служить в армии.\n"
                    "Чем больше больниц — тем больше рабочих."
                ),
                "Сырье": (
                    "Потребляемый ресурс,\nнеобходимый для поддержания армии и населения.\n"
                    "Добыча зависит от количества фабрик."
                ),
                "Население": (
                    "Платят налоги\nи потребляют сырьё.\n"
                    "Растёт при росте рабочих.\nУмирают если нет сырья."
                ),
                "Потребление": (
                    "Уровень потребления сырья армией.\n"
                    "Если превышает лимит армии — армия умирает от голода."
                ),
                "Лимит армии": (
                    "Текущий максимальный лимит,\nпотребления армией сырья.\n"
                    "Зависит от количества городов фракции."
                )
            }.get(res_name, "Информация о ресурсе недоступна.")

            # Label с текстом информации
            label = Label(
                text=info_text,
                font_size=sp(16),
                color=(0.9, 0.9, 0.9, 1),
                halign='left',
                valign='top',
                size_hint_y=None,
                padding=[dp(15), dp(10)]
            )

            # Привязка высоты к размеру текста
            label.bind(
                width=lambda *x: label.setter('text_size')(label, (label.width, None)),
                texture_size=lambda *x: label.setter('height')(label, label.texture_size[1])
            )

            # ScrollView для длинного текста
            scroll_view = ScrollView(size_hint=(1, 1))
            scroll_view.add_widget(label)

            # Кнопка закрытия
            close_btn = Button(
                text="Закрыть",
                size_hint=(1, None),
                height=dp(50),
                font_size=sp(18),
                background_color=(0.2, 0.6, 0.8, 1),
                background_normal='',
                on_press=lambda btn: popup.dismiss()
            )

            # Общий контент попапа
            content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
            content.add_widget(scroll_view)
            content.add_widget(close_btn)

            # Само окно Popup
            popup = Popup(
                title=res_name,
                content=content,
                size_hint=(0.8, 0.6),
                title_size=sp(20),
                title_align='center',
                background_color=(0.1, 0.1, 0.1, 0.98),
                separator_color=(0.3, 0.3, 0.3, 1),
                auto_dismiss=False  # чтобы случайно не закрыть вне кнопки
            )

            # Привязываем закрытие к кнопке
            close_btn.bind(on_release=popup.dismiss)

            # Открываем попап
            popup.open()

        # --- Рендеринг строк ---
        items = list(resources.items())
        for idx, (res_name, formatted) in enumerate(items):
            # Разделитель сверху
            line = Widget(size_hint=(1, None), height=dp(1))
            with line.canvas:
                Color(0.5, 0.5, 0.5, 1)
                rect = Rectangle(pos=(self.x + self.padding[0], 0),
                                 size=(self.width - (self.padding[0] + self.padding[2]), dp(1)))
                line.bind(pos=lambda inst, val: setattr(rect, 'pos', (self.x + self.padding[0], val[1])),
                          size=lambda inst, sz: setattr(rect, 'size',
                                                        (self.width - (self.padding[0] + self.padding[2]), dp(1))))

            widgets.append(line)

            # Строка с ресурсом
            row = BoxLayout(orientation='horizontal', size_hint=(1, None), height=row_h, spacing=dp(4))

            icon_path = self.ICON_MAP.get(res_name)
            if icon_path:
                img = Image(source=icon_path, size_hint=(None, None), size=(icon_size, icon_size), allow_stretch=True)
            else:
                img = Widget(size_hint=(None, None), size=(icon_size, icon_size))

            lbl_colon = Label(
                text=":",
                font_size=sp(16),
                color=(1, 1, 1, 1),
                size_hint=(None, None),
                size=(colon_w, row_h),
                halign='center',
                valign='middle'
            )
            lbl_colon.text_size = (colon_w, row_h)

            num = parsed.get(res_name)
            val_color = (1, 0, 0, 1) if (num is not None and num < 0) or (
                    res_name == "Потребление" and num > parsed.get("Лимит армии", 0)) else (1, 1, 1, 1)

            lbl_val = Label(
                text=str(formatted),
                font_size=sp(16),
                color=val_color,
                size_hint=(None, None),
                size=(val_w, row_h),
                halign='left',
                valign='middle'
            )
            lbl_val.text_size = (val_w, row_h)
            self._label_values[res_name] = lbl_val

            row.add_widget(img)
            row.add_widget(Widget(size_hint=(None, None), size=(gap, row_h)))
            row.add_widget(lbl_colon)
            row.add_widget(Widget(size_hint=(None, None), size=(gap, row_h)))
            row.add_widget(lbl_val)

            # Добавляем обработчик тапа по строке для показа подсказки
            row.bind(
                on_touch_down=lambda instance, touch, name=res_name: show_tooltip(name) if instance.collide_point(
                    touch.x, touch.y) else False
            )

            widgets.append(row)

        # Нижний разделитель
        last_line = Widget(size_hint=(1, None), height=dp(1))
        with last_line.canvas:
            Color(0.5, 0.5, 0.5, 1)
            rect = Rectangle(pos=(self.x + self.padding[0], 0),
                             size=(self.width - (self.padding[0] + self.padding[2]), dp(1)))
            last_line.bind(pos=lambda inst, val: setattr(rect, 'pos', (self.x + self.padding[0], val[1])),
                           size=lambda inst, sz: setattr(rect, 'size',
                                                         (self.width - (self.padding[0] + self.padding[2]), dp(1))))

        widgets.append(last_line)

        # Добавляем все виджеты
        for w in widgets:
            self.add_widget(w)

        # Расчёт высоты
        num_rows = len(items)
        sep_h = dp(1)
        rows_h = num_rows * row_h
        lines_h = (num_rows + 1) * sep_h
        total_h_raw = self.padding[1] + self.padding[3] + rows_h + lines_h
        max_bottom_y = Window.height * 0.35
        max_allowed_h = Window.height - max_bottom_y
        final_h = min(total_h_raw, max_allowed_h)
        self.height = final_h


# Класс для кнопки с изображением
class ImageButton(ButtonBehavior, Image):
    pass


class CircularProgressButton(Button):
    progress = NumericProperty(0)

    def __init__(self, duration=1.5, **kwargs):
        super().__init__(**kwargs)
        self.duration = duration
        self.anim = None
        self.bind(size=self.draw_circle, pos=self.draw_circle)

    def draw_circle(self, *args):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.3)  # Цвет индикатора
            self.circle = Line(
                circle=(self.center_x, self.center_y, min(self.width, self.height) / 2 - dp(8), 0, 0),
                width=dp(4),
                cap='round'
            )

    def start_progress(self):
        if self.anim:
            return
        self.progress = 0
        self.disabled = True
        self.canvas.after.clear()

        with self.canvas.after:
            Color(1, 1, 1, 0.3)
            self.circle = Line(
                circle=(self.center_x, self.center_y, min(self.width, self.height) / 2 - dp(8), 0, 0),
                width=dp(4),
                cap='round'
            )

        anim = Animation(progress=360, duration=self.duration, t='linear')
        anim.bind(on_progress=self.update_arc)
        anim.bind(on_complete=self.reset_button)
        self.anim = anim
        anim.start(self)

    def update_arc(self, animation, instance, value):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.3)
            self.circle = Line(
                circle=(
                    self.center_x,
                    self.center_y,
                    min(self.width, self.height) / 2 - dp(8),
                    0,
                    self.progress
                ),
                width=dp(4),
                cap='round'
            )

    def reset_button(self, *args):
        self.disabled = False
        self.anim = None
        self.canvas.after.clear()


class GameScreen(Screen):
    SEASON_NAMES = ['Зима', 'Весна', 'Лето', 'Осень']
    SEASON_ICONS = ['snowflake', 'green_leaf', 'sun', 'yellow_leaf']

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
        self.prev_diplomacy_state = {}
        # Инициализация AI-контроллеров
        self.ai_controllers = {}
        # Инициализация EventManager
        self.event_manager = EventManager(self.selected_faction, self, self.game_state_manager.faction)
        # Инициализация UI
        self.is_android = platform == 'android'
        self.season_manager = SeasonManager()
        self.current_idx = random.randint(0, 3)
        current_season = {
            'name': self.SEASON_NAMES[self.current_idx],
            'icon': self.SEASON_ICONS[self.current_idx]
        }
        self.init_ui()
        self._update_season_display(current_season)
        self.season_manager.update(self.current_idx)
        # Запускаем обновление ресурсов каждую 1 секунду
        Clock.schedule_interval(self.update_cash, 1)
        # Запускаем обновление рейтинга армии каждые 1 секунду
        Clock.schedule_interval(self.update_army_rating, 1)

    def save_selected_faction_to_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("INSERT INTO user_faction (faction_name) VALUES (?)", (self.selected_faction,))

        conn.commit()
        conn.close()

    def init_ui(self):
        self.season_container = FloatLayout(
            size_hint=(None, None),
            size=(dp(120), dp(50)),
            pos_hint={'right': 0.86, 'top': 1}
        )
        # Фон под «сезон» (скруглённый прямоугольник)
        with self.season_container.canvas.before:
            Color(0.15, 0.2, 0.3, 0.9)
            self._season_bg = RoundedRectangle(radius=[10])

        def _upd_bg(instance, value):
            self.season_container.canvas.before.clear()
            with self.season_container.canvas.before:
                Color(0.15, 0.2, 0.3, 0.9)
                self._season_bg = RoundedRectangle(pos=instance.pos, size=instance.size, radius=[10])

        self.season_container.bind(pos=_upd_bg, size=_upd_bg)

        # Image: иконка сезона
        self.season_icon = Image(
            source='',  # сюда позже запишем путь к нужной иконке
            size_hint=(None, None),
            size=(dp(40), dp(30)),
            pos_hint={'x': 0.02, 'center_y': 0.5}
        )
        # Label: название сезона
        self.season_label = Label(
            text='',  # сюда позже запишем текст («Зима», «Лето» и т.п.)
            font_size=sp(16),
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(80), dp(30)),
            pos_hint={'x': 0.35, 'center_y': 0.5},
            halign='left',
            valign='middle'
        )
        self.season_label.bind(size=self.season_label.setter('text_size'))

        self.season_container.add_widget(self.season_icon)
        self.season_container.add_widget(self.season_label)
        self.add_widget(self.season_container)

        self.season_container.bind(on_touch_down=self.on_season_pressed)

        # === Контейнер для кнопки "Завершить ход" ===
        end_turn_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(160), dp(75)),
            pos_hint={'x': 0, 'y': 0.31},
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

        # === Кнопка с анимацией заполнения ===
        self.end_turn_button = CircularProgressButton(
            text="Завершить ход",
            font_size=sp(20),
            bold=True,
            color=(1, 1, 1, 1),
            background_color=(0, 0, 0, 0),
            size_hint=(1, 1),
            duration=1.4  # Время анимации в секундах
        )

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
        mode_panel_width = dp(90)
        mode_panel_container = BoxLayout(
            orientation='vertical',
            size_hint=(None, 0.82),
            width=mode_panel_width,
            pos_hint={'right': 1, 'top': 0.96},
            padding=dp(10),
            spacing=dp(16)
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
                                  size_hint=(1, None), height=dp(60), on_release=self.show_advisor)
        btn_economy = ImageButton(source='files/status/economy.png', size_hint=(1, None), height=dp(60),
                                  on_release=self.switch_to_economy)
        btn_army = ImageButton(source='files/status/army.png', size_hint=(1, None), height=dp(60),
                               on_release=self.switch_to_army)
        btn_politics = ImageButton(source='files/status/politic.png', size_hint=(1, None), height=dp(60),
                                   on_release=self.switch_to_politics)
        mode_panel_container.add_widget(btn_advisor)
        mode_panel_container.add_widget(btn_economy)
        mode_panel_container.add_widget(btn_army)
        mode_panel_container.add_widget(btn_politics)
        self.add_widget(mode_panel_container)
        self.save_interface_element("ModePanel", "bottom", mode_panel_container)

        # === Центральная область ===
        self.game_area = FloatLayout(size_hint=(0.7, 1), pos_hint={'x': 0.25, 'y': 0})
        self.add_widget(self.game_area)
        self.save_interface_element("GameArea", "center", self.game_area)

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
            size=(dp(100) if self.is_android else 100, dp(50) if self.is_android else 50),
            pos_hint={'x': 0.89, 'y': 0},
            padding=dp(10),
            spacing=dp(4)
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
            font_size='15sp',
            bold=True,
            color=(1, 1, 1, 1)
        )
        self.exit_button.bind(on_release=lambda x: self.confirm_exit())
        exit_container.add_widget(self.exit_button)
        self.add_widget(exit_container)

        # === ResourceBox ===
        # Инициализируем ResourceBox с фиксированным размером
        self.resource_box = ResourceBox(resource_manager=self.faction)
        self.add_widget(self.resource_box)

        # Сохраняем координаты ResourceBox
        self.save_interface_element("ResourceBox", "top_left", self.resource_box)

        # === Инициализация ИИ ===
        self.init_ai_controllers()

        def on_end_turn(instance):
            instance.start_progress()
            self.process_turn(None)
            Clock.schedule_once(lambda dt: instance.reset_button(), 1.5)  # Ждём 1.5 секунды и сбрасываем кнопку

        self.end_turn_button.bind(on_release=on_end_turn)
        end_turn_container.add_widget(self.end_turn_button)
        self.add_widget(end_turn_container)
        self.save_interface_element("EndTurnButton", "bottom_right", self.end_turn_button)

    def update_resource_box_position(self, *args):
        """Обновляет позицию ResourceBox так, чтобы он всегда был в левом верхнем углу."""
        if self.resource_box:
            self.resource_box.pos = (dp(0), Window.height - self.resource_box.height)

    def _update_season_display(self, season_info: dict):
        """
        Получив словарь вида {'name': 'Зима', 'icon': 'snowflake'},
        обновляем иконку и подпись в интерфейсе.
        Предполагается, что у вас есть набор png (или других) иконок:
        например 'icons/snowflake.png', 'icons/green_leaf.png', 'icons/sun.png', 'icons/yellow_leaf.png'.
        """
        # Делайте путь к иконке так, как вам удобно:
        icon_map = {
            'snowflake': 'files/status/icons/snowflake.png',
            'green_leaf': 'files/status/icons/green_leaf.png',
            'sun': 'files/status/icons/sun.png',
            'yellow_leaf': 'files/status/icons/yellow_leaf.png'
        }
        icon_key = season_info.get('icon', '')
        if icon_key in icon_map:
            self.season_icon.source = icon_map[icon_key]
        else:
            self.season_icon.source = ''

        self.season_label.text = season_info.get('name', '')

    def check_diplomacy_changes(self):
        """
        Проверяет изменения в дипломатических отношениях между текущей фракцией и другими.
        Если статус меняется, отображается соответствующее сообщение.
        """

        current_faction = self.selected_faction

        # Сохраняем предыдущее состояние, если оно еще не было загружено
        if not hasattr(self, 'prev_diplomacy_state'):
            self.prev_diplomacy_state = {}
        message = "фракци"
        try:
            # Получаем текущие отношения для текущей фракции
            self.cursor.execute("""
                SELECT faction2, relationship FROM diplomacies
                WHERE faction1 = ?
            """, (current_faction,))
            current_records = dict(self.cursor.fetchall())

            # Словарь для хранения изменений по типам
            changes = {
                "война": [],
                "нейтралитет": [],
                "союз": [],
                "уничтожена": []
            }

            # Проверяем изменения по сравнению с предыдущим ходом
            for faction, status in current_records.items():
                prev_status = self.prev_diplomacy_state.get(faction)
                if prev_status is None:
                    continue  # Пропускаем первоначальную инициализацию
                if prev_status != status:
                    changes[status].append(faction)

            # Отправляем уведомления на основе изменений
            for status_type, factions_list in changes.items():
                if not factions_list:
                    continue

                if status_type == "война":
                    message_prefix = f"Война с {message}ей"
                    if len(factions_list) > 1:
                        message = f"Война с {message}ями: {', '.join(factions_list)}"
                    else:
                        message = f"{message_prefix} {factions_list[0]}"
                elif status_type == "нейтралитет":
                    message_prefix = f"Заключён мир с {message}ей"
                    if len(factions_list) > 1:
                        message = f"Заключён мир с {message}ями: {', '.join(factions_list)}"
                    else:
                        message = f"{message_prefix} {factions_list[0]}"
                elif status_type == "союз":
                    message_prefix = f"Теперь дружим с {message}ей"
                    if len(factions_list) > 1:
                        message = f"Теперь дружим с {message}ями: {', '.join(factions_list)}"
                    else:
                        message = f"{message_prefix} {factions_list[0]}"
                elif status_type == "уничтожена":
                    message_prefix = "фракци"
                    if len(factions_list) > 1:
                        message = f"{message_prefix}и: {', '.join(factions_list)} уничтожены"
                    else:
                        message = f"{message_prefix}я {factions_list[0]} уничтожена"

                self.show_notification(message)

            # Обновляем предыдущее состояние
            self.prev_diplomacy_state = current_records.copy()

        except sqlite3.Error as e:
            print(f"Ошибка при проверке дипломатических отношений: {e}")

    def show_notification(self, message, title="Новость дня"):

        # === Цветовая схема и стили ===
        background_color = (0.1, 0.1, 0.1, 0.95)  # Тёмный фон (Material-стиль)
        button_color = (0.2, 0.6, 0.8, 1)  # Акцентный цвет кнопки
        text_color = (1, 1, 1, 1)

        # === Основной контент ===
        content = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))

        # === Метка с текстом ===
        label = Label(
            text=message,
            font_size=sp(18),
            halign='center',
            valign='middle',
            color=text_color,
            size_hint_y=0.7
        )
        label.bind(size=label.setter('text_size'))  # Центрирование текста

        # === Кнопка закрытия ===
        close_button = Button(
            text="Ну что теперь поделать...",
            size_hint=(1, 0.3),
            background_color=button_color,
            font_size=sp(16),
            bold=True,
            color=(1, 1, 1, 1)
        )

        # === Добавляем элементы ===
        content.add_widget(label)
        content.add_widget(close_button)

        # === Создаём попап ===
        popup = Popup(
            title=title,
            title_size=sp(20),
            title_color=text_color,
            content=content,
            size_hint=(0.8, None),
            height=dp(250),
            background_color=background_color,
            separator_color=(0.3, 0.3, 0.3, 1)
        )

        # Привязываем кнопку к закрытию
        close_button.bind(on_release=popup.dismiss)

        # Открываем
        popup.open()

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
        self.check_diplomacy_changes()
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
        # Обновляем текущий сезон
        new_season = self.update_season(self.turn_counter)
        self._update_season_display(new_season)
        self.season_manager.update(self.current_idx)
        print("Здесь должны вызываться функции отрисовки звезд мощи городов")
        # Обновляем статус городов и отрисовываем звёздочки мощи армий
        # Принудительно обновляем рейтинг один раз
        self.update_army_rating()
        # Логирование или обновление интерфейса после хода
        print(f"Ход {self.turn_counter} завершён")

        self.event_now = random.randint(1, 100)
        # Проверяем, нужно ли запустить событие
        if self.turn_counter % self.event_now == 0:
            print("Генерация события...")
            self.event_manager.generate_event(self.turn_counter)

    def update_season(self, turn_count: int) -> dict:
        """
        Вызываем каждый ход, передавая turn_count.
        Если turn_count кратно 4, переключаем current_idx на следующий сезон.
        Возвращаем {'name': <название>, 'icon': <иконка>}.
        """
        if turn_count > 1 and (turn_count - 1) % 4 == 0:
            # Переходим к следующему сезону
            self.current_idx = (self.current_idx + 1) % 4

        return {
            'name': self.SEASON_NAMES[self.current_idx],
            'icon': self.SEASON_ICONS[self.current_idx]
        }

    def on_season_pressed(self, instance, touch):
        """
        Показывает информационное окно с эффектом текущего сезона
        для выбранной фракции при клике (касании) внутри season_container.
        """
        if instance.collide_point(touch.x, touch.y):
            # Текущий индекс сезона в SeasonManager
            current_idx = self.current_idx
            current_season_name = self.SEASON_NAMES[current_idx]

            # Извлекаем коэффициенты именно для этой фракции
            faction = self.selected_faction
            try:
                coeffs = SeasonManager.FACTION_EFFECTS[current_idx][faction]
            except KeyError:
                # Если вдруг нечаянно фракции или сезона нет — выводим заглушку
                effect_text = "Информация о бонусах для вашей фракции недоступна."
            else:
                stat_f = coeffs['stat']
                cost_f = coeffs['cost']

                parts = []
                # Если stat_f != 1.0, вычисляем процент изменения атаки/защиты
                if stat_f != 1.0:
                    stat_pct = (stat_f - 1.0) * 100
                    # Округляем до ближайшего целого
                    stat_pct_int = int(abs(round(stat_pct)))
                    sign = '+' if stat_pct > 0 else '-'
                    parts.append(f"{sign}{stat_pct_int}% к Урону и Защите")

                # Если cost_f != 1.0, вычисляем процент изменения стоимости
                if cost_f != 1.0:
                    cost_pct = (cost_f - 1.0) * 100
                    cost_pct_int = int(abs(round(cost_pct)))
                    sign = '+' if cost_pct > 0 else '-'
                    parts.append(f"{sign}{cost_pct_int}% к стоимости юнитов")

                # Если ни stat, ни cost нет изменений (коэффициент 1.0) — делаем общий текст
                if not parts:
                    effect_text = "Нет изменений для вашей фракции в этом сезоне."
                else:
                    effect_text = ", ".join(parts)

            # ---------- Определяем адаптивные размеры ----------
            popup_width = Window.width * 0.9
            popup_height = Window.height * 0.45

            if platform == 'android':
                label_font = sp(18)
                button_font = sp(16)
                button_height_dp = dp(46)
                padding_dp = dp(18)
                spacing_dp = dp(13)
            else:
                label_font = sp(18)
                button_font = sp(16)
                button_height_dp = dp(46)
                padding_dp = dp(18)
                spacing_dp = dp(13)

            # ---------- Собираем контент Popup ----------
            content = BoxLayout(
                orientation='vertical',
                padding=padding_dp,
                spacing=spacing_dp
            )

            # Маркированный текст: жирным показываем название сезона, дальше — effect_text
            label = Label(
                text=f"{effect_text}",
                font_size=label_font,
                halign='center',
                valign='middle',
                markup=True,
                color=(1, 1, 1, 1),
                size_hint_y=None
            )
            label.text_size = (popup_width - 2 * padding_dp, None)
            label.texture_update()
            label.height = label.texture_size[1] + dp(10)

            btn_close = Button(
                text="Закрыть",
                size_hint=(1, None),
                height=button_height_dp,
                background_normal='',
                background_color=(0.2, 0.6, 0.8, 1),
                font_size=button_font,
                bold=True,
                color=(1, 1, 1, 1)
            )

            content.add_widget(label)
            content.add_widget(btn_close)

            popup = Popup(
                title=f"Эффект сезона. {self.selected_faction}",
                title_align='center',
                title_size=sp(20) if platform != 'android' else sp(22),
                title_color=(1, 1, 1, 1),
                content=content,
                size_hint=(None, None),
                size=(popup_width, popup_height),
                background_color=(0.1, 0.1, 0.1, 0.95),
                separator_color=(0.3, 0.3, 0.3, 1),
                auto_dismiss=False
            )

            btn_close.bind(on_release=popup.dismiss)
            popup.open()
            return True

        return False

    def confirm_exit(self):
        # === Создаём основное содержимое Popup с отступами ===
        content = BoxLayout(
            orientation='vertical',
            spacing=dp(15),
            padding=[dp(20), dp(20), dp(20), dp(20)]
        )

        # --- Сообщение с увеличенным шрифтом и адаптивной шириной ---
        message = Label(
            text="Устали, Ваше Величество?",
            font_size=sp(18),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint=(1, None)
        )

        # Привязываем ширину сообщения к ширине Popup (учитываем паддинг)
        def update_message_size(instance, width):
            # width здесь — ширина content, без padding по горизонтали
            message.text_size = (width, None)
            message.texture_update()
            message.height = message.texture_size[1] + dp(10)

        content.bind(width=update_message_size)
        # Инициализируем высоту сразу
        update_message_size(message, Window.width * 0.95 - dp(10))

        # --- Горизонтальный контейнер для кнопок ---
        btn_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=dp(48),
            spacing=dp(10)
        )

        # --- Кнопка «Да» (красная) ---
        btn_yes = Button(
            text="Да",
            size_hint=(1, 1),
            background_normal='',
            background_color=hex_color('#E53E3E'),
            font_size=sp(16),
            bold=True,
            color=(1, 1, 1, 1)
        )

        # --- Кнопка «Нет» (зелёная) ---
        btn_no = Button(
            text="Нет",
            size_hint=(1, 1),
            background_normal='',
            background_color=hex_color('#38A169'),
            font_size=sp(16),
            bold=True,
            color=(1, 1, 1, 1)
        )

        btn_container.add_widget(btn_yes)
        btn_container.add_widget(btn_no)

        # Добавляем метку и контейнер с кнопками в основной контент
        content.add_widget(message)
        content.add_widget(btn_container)

        # --- Создаём сам Popup, делаем его адаптивным по размеру экрана ---
        popup = Popup(
            title="Подтверждение выхода из матча",
            title_size=sp(20),
            title_align='center',
            title_color=(1, 1, 1, 1),
            content=content,
            size_hint=(0.9, None),
            height=Window.height * 0.51,
            background_color=(0.1, 0.1, 0.1, 0.95),
            separator_color=(0.3, 0.3, 0.3, 1),
            auto_dismiss=False
        )

        # --- Привязываем действия к кнопкам ---
        btn_yes.bind(on_release=lambda x: (popup.dismiss(), App.get_running_app().restart_app()))
        btn_no.bind(on_release=popup.dismiss)

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
        Window.unbind(on_resize=self.update_resource_box_position)
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

    def update_army_rating(self, dt=None):
        """Обновляет рейтинг армии и отрисовывает звёзды над городами."""
        self.update_city_military_status()
        self.draw_army_stars_on_map()

    def draw_army_stars_on_map(self):
        """
        Рисует звёздочки над иконками городов.
        Использует готовые координаты из self.city_star_levels:
            { city_name: (star_level, icon_x, icon_y, city_name) }
        """
        star_img_path = 'files/status/army_in_city/star.png'
        if not os.path.exists(star_img_path):
            print(f"Файл звезды не найден: {star_img_path}")
            return

        # Параметры отрисовки
        STAR_SIZE = 25
        SPACING = 5
        CITY_ICON_SIZE = 77

        # Если нет данных — ничего не рисуем
        if not hasattr(self, 'city_star_levels') or not self.city_star_levels:
            return

        # Очищаем прошлые звёзды
        self.game_area.canvas.before.clear()

        with self.game_area.canvas.before:
            for city_id, data in self.city_star_levels.items():
                star_level, icon_x, icon_y, city_name = data
                if star_level <= 0:
                    continue

                # Центр иконки
                icon_center_x = icon_x + CITY_ICON_SIZE / 2
                icon_center_y = icon_y + CITY_ICON_SIZE / 2

                # Общая ширина всех звёздочек
                total_width = STAR_SIZE * star_level + SPACING * (star_level - 1)

                # Смещаем так, чтобы центр звёзд совпадал с центром иконки
                start_x = icon_center_x - total_width / 2
                start_y = icon_center_y + 20  # чуть выше центра иконки

                # Рисуем каждую звезду
                for i in range(star_level):
                    x_i = start_x + i * (STAR_SIZE + SPACING)
                    y_i = start_y
                    Rectangle(
                        source=star_img_path,
                        pos=(x_i, y_i),
                        size=(STAR_SIZE, STAR_SIZE)
                    )

    def get_total_army_strength_by_faction(self, faction):
        """Возвращает общую мощь армии фракции."""
        class_coefficients = {
            "1": 1.3,
            "2": 1.7,
            "3": 2.0,
            "4": 3.0,
            "5": 4.0
        }
        try:
            self.cursor.execute("""
                SELECT g.unit_name, g.unit_count, u.attack, u.defense, u.durability, u.unit_class
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE u.faction = ?
                  AND g.city_id IN (SELECT name FROM cities WHERE faction = ?)
            """, (faction, faction))
            rows = self.cursor.fetchall()
            total_strength = 0
            for row in rows:
                unit_name, count, attack, defense, durability, unit_class = row
                coefficient = class_coefficients.get(unit_class, 1.0)
                unit_strength = (attack * coefficient) + defense + durability
                total_strength += unit_strength * count
            return total_strength
        except sqlite3.Error as e:
            print(f"Ошибка при подсчёте общей мощи армии: {e}")
            return 0

    def get_city_army_strength_by_faction(self, city_id, faction):
        """Возвращает мощь армии фракции в конкретном городе."""
        class_coefficients = {
            "1": 1.3,
            "2": 1.7,
            "3": 2.0,
            "4": 3.0,
            "5": 4.0
        }
        try:
            self.cursor.execute("""
                SELECT g.unit_name, g.unit_count, u.attack, u.defense, u.durability, u.unit_class
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE g.city_id = ? AND u.faction = ?
            """, (city_id, faction))
            rows = self.cursor.fetchall()
            city_strength = 0
            for row in rows:
                unit_name, count, attack, defense, durability, unit_class = row
                coefficient = class_coefficients.get(unit_class, 1.0)
                unit_strength = (attack * coefficient) + defense + durability
                city_strength += unit_strength * count
            return city_strength
        except sqlite3.Error as e:
            print(f"Ошибка при подсчёте мощи города {city_id}: {e}")
            return 0

    def calculate_star_level(self, total_strength, city_strength):
        """Возвращает уровень (количество звездочек) на основе процентного соотношения мощи."""
        if total_strength == 0 or city_strength == 0:
            return 0  # Нет войск — нет звёздочек

        percent = (city_strength / total_strength) * 100

        if percent < 25:
            return 1
        elif 25 <= percent < 75:
            return 2
        elif 75 <= percent <= 100:
            return 3
        else:
            return 3  # На случай, если процент > 100 из-за ошибок округления

    def update_city_military_status(self):
        """
        Для всех фракций:
          1) Находим все города, где есть гарнизоны
          2) Для каждой фракции считаем общую мощь армии
          3) Для каждого города этой фракции считаем его мощь
          4) Вычисляем star_level = 0–3
          5) Сохраняем в self.city_star_levels:
             { city_name: (star_level, icon_x, icon_y, city_name) }
        """
        try:
            self.cursor.execute("""
                SELECT name, faction, icon_coordinates 
                FROM cities 
                WHERE icon_coordinates IS NOT NULL
            """)
            raw_cities = self.cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка при получении городов с гарнизонами: {e}")
            self.city_star_levels = {}
            return

        if not raw_cities:
            print("Нет городов с гарнизонами.")
            self.city_star_levels = {}
            return

        from collections import defaultdict
        factions_cities = defaultdict(list)
        for city_name, faction, coords_str in raw_cities:
            factions_cities[faction].append((city_name, coords_str))

        new_dict = {}

        for faction, cities_list in factions_cities.items():
            total_strength = self.get_total_army_strength_by_faction(faction)
            if total_strength == 0:
                continue

            for city_name, coords_str in cities_list:
                try:
                    coords = eval(coords_str)  # лучше заменить на ast.literal_eval
                    icon_x, icon_y = coords
                except Exception as ex:
                    print(f"Ошибка парсинга icon_coordinates для {city_name}: {ex}")
                    continue

                city_strength = self.get_city_army_strength_by_faction(city_name, faction)

                if city_strength == 0:
                    star_level = 0
                else:
                    percent = (city_strength / total_strength) * 100
                    if percent < 35:
                        star_level = 1
                    elif percent < 65:
                        star_level = 2
                    else:
                        star_level = 3

                new_dict[city_name] = (star_level, icon_x, icon_y, city_name)


        self.city_star_levels = new_dict


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

    def save_interface_element(self, element_name, screen_section, widget):
        """Сохраняет координаты и размер элемента интерфейса в базу данных."""
        if not self.conn:
            return

        try:
            pos = widget.pos
            size = widget.size
            pos_hint = str(widget.pos_hint) if widget.pos_hint else None

            self.cursor.execute('''
                INSERT INTO interface_coord (
                    element_name, screen_section, x, y, width, height, size_hint_x, size_hint_y, pos_hint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                element_name,
                screen_section,
                pos[0], pos[1],
                size[0], size[1],
                widget.size_hint[0] if widget.size_hint[0] is not None else None,
                widget.size_hint[1] if widget.size_hint[1] is not None else None,
                pos_hint
            ))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении координат {element_name}: {e}")

    def reset_game(self):
        """Сброс игры (например, при новой игре)."""
        self.save_turn(self.selected_faction, 0)  # Сбрасываем счетчик ходов до 0
        self.turn_counter = 0
        print("Счетчик ходов сброшен.")