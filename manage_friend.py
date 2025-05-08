

from kivy.clock import Clock
from kivy.properties import partial, StringProperty, NumericProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Line, Color, RoundedRectangle
from kivy.uix.scrollview import ScrollView
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.progressbar import ProgressBar
from kivy.metrics import dp
from kivy.core.window import Window
import sqlite3
import time

from kivy.uix.widget import Widget
from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'


STYLE_BUTTON = {
    'background_normal': '',
    'color': (1, 1, 1, 1),
    'size_hint_y': None,
    'height': dp(40),
}
STYLE_BUTTON_ACTION = {
    'background_normal': '',
    'color': (1, 1, 1, 1),
}
STYLE_BUTTON_DANGER = {
    'background_normal': '',
    'color': (1, 1, 1, 1),
}
STYLE_LABEL_HEADER = {
    'bold': True,
    'color': (0.9, 0.9, 0.9, 1),
    'font_size': dp(16),
}
STYLE_LABEL_TEXT = {
    'color': (0.8, 0.8, 0.8, 1),
}


class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=self.background_color)
            self.rect = RoundedRectangle(
                size=self.size,
                pos=self.pos,
                radius=[dp(10)] * 4
            )
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class StyledDropDown(DropDown):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_width = False
        self.width = dp(200)
        with self.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.bg = RoundedRectangle(
                size=self.size,
                pos=self.pos,
                radius=[dp(5)] * 4
            )
        self.bind(size=self._update_bg, pos=self._update_bg)

    def _update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

def has_pending_action():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM last_click")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def get_city_faction(city_name):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT faction FROM cities WHERE name=?", (city_name,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_allies_for_faction(faction_name):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT faction1, faction2 FROM diplomacies "
        "WHERE (faction1=? OR faction2=?) AND relationship='союз'",
        (faction_name, faction_name)
    )
    allies = {
        row[1] if row[0] == faction_name else row[0]
        for row in cur.fetchall()
    }
    conn.close()
    return allies


class ManageFriend(Popup):
    """
    Окно союзников с улучшенным дизайном
    """
    def __init__(self, faction_name, game_area, **kwargs):
        super().__init__(**kwargs)
        self.faction_name = faction_name
        self.title = f"Союзник фракции {faction_name}"
        self.title_size = dp(18)
        self.title_color = (0.9, 0.9, 0.9, 1)
        self.separator_color = (0.3, 0.6, 0.8, 1)
        self.separator_height = dp(2)
        self.size_hint = (0.85, 0.85)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.background = 'atlas://data/images/defaulttheme/modalview-background'
        self.background_color = (0.1, 0.1, 0.15, 0.9)
        self.selection_mode = None
        self.selected_ally = None
        self.highlighted_city = None
        self.status_label = Label(
            text="",
            size_hint_y=None,
            height=dp(30),
            **STYLE_LABEL_TEXT
        )
        self._build_content()

    def _show_fullscreen_message(self, message):
        """
        Отображает всплывающее сообщение на весь экран
        """
        popup = ModalView(
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0.8),  # Полупрозрачный фон
            auto_dismiss=True  # Автоматически закрывается при клике
        )
        content = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(10)
        )
        label = Label(
            text=message,
            font_size=dp(24),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        label.bind(size=label.setter('text_size'))  # Для корректного выравнивания текста
        close_button = StyledButton(
            text="Закрыть",
            background_color=(0.2, 0.6, 0.8, 1),
            size_hint_y=None,
            height=dp(50)
        )
        close_button.bind(on_release=popup.dismiss)
        content.add_widget(label)
        content.add_widget(close_button)
        popup.add_widget(content)
        popup.open()

    def _finalize_city_selection(self, city_name, action, ally):
        city_faction = get_city_faction(city_name)
        allies = get_allies_for_faction(self.faction_name)
        if action == "defense":
            if city_faction == self.faction_name:
                self.save_query_defense_to_db(city_name)
                self.status_label.text = f"Запрос на защиту города {city_name} отправлен."
                self._show_fullscreen_message(f"Город для защиты выбран: {city_name}")
            else:
                self.status_label.text = "Нельзя защищать чужие города."
        elif action == "attack":
            if city_faction != self.faction_name and city_faction not in allies:
                self.save_query_attack_to_db(city_name)
                self.status_label.text = f"Запрос на атаку города {city_name} отправлен."
                self._show_fullscreen_message(f"Город для атаки выбран: {city_name}")
            else:
                self.status_label.text = "Нельзя атаковать дружественные города."
        self.progress_bar.opacity = 0

    def _build_content(self):
        # Основной контейнер
        main_container = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(15)
        )

        # Фон основного контейнера
        with main_container.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.main_bg = RoundedRectangle(
                size=main_container.size,
                pos=main_container.pos,
                radius=[dp(10)] * 4
            )
            main_container.bind(
                pos=lambda *x: setattr(self.main_bg, 'pos', main_container.pos),
                size=lambda *x: setattr(self.main_bg, 'size', main_container.size)
            )

        # Таблица союзников
        main_container.add_widget(self._create_table())

        # Прогресс-бар с кастомной отрисовкой
        self.progress_bar = ProgressBar(
            max=100,
            size_hint_y=None,
            height=dp(20)
        )
        self.progress_bar.opacity = 0

        with self.progress_bar.canvas.before:
            # Фон прогрессбара
            Color(0.3, 0.3, 0.3, 1)
            self.progress_bg = RoundedRectangle(
                size=self.progress_bar.size,
                pos=self.progress_bar.pos,
                radius=[dp(5)] * 4
            )
            # Активная часть
            Color(0.2, 0.6, 0.8, 1)
            self.progress_rect = RoundedRectangle(
                size=(0, self.progress_bar.height),
                pos=self.progress_bar.pos,
                radius=[dp(5)] * 4
            )

        self.progress_bar.bind(
            pos=self.update_progress_graphics,
            size=self.update_progress_graphics,
            value=self.update_progress_graphics
        )

        # Статус бар
        status_box = BoxLayout(size_hint_y=None, height=dp(70))
        status_content = BoxLayout(orientation='vertical', spacing=dp(5))
        status_content.add_widget(self.status_label)
        status_content.add_widget(self.progress_bar)
        status_box.add_widget(status_content)
        main_container.add_widget(status_box)

        # Кнопки управления
        button_box = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )

        close_btn = StyledButton(
            text="Закрыть",
            background_color=(0.2, 0.6, 0.8, 1),
            **STYLE_BUTTON
        )
        close_btn.bind(on_release=lambda btn: self.dismiss())

        button_box.add_widget(close_btn)
        main_container.add_widget(button_box)

        self.content = main_container

    def update_progress_graphics(self, *args):
        self.progress_bg.pos = self.progress_bar.pos
        self.progress_bg.size = self.progress_bar.size
        self.progress_rect.pos = self.progress_bar.pos
        self.progress_rect.size = (
            self.progress_bar.value_normalized * self.progress_bar.width,
            self.progress_bar.height
        )

        self.progress_rect.pos = self.progress_bar.pos

    def _create_table(self):
        allies = self._get_allies_from_db()

        main_container = BoxLayout(
            orientation='vertical',
            spacing=dp(15),
            padding=dp(20),
            size_hint_y=None
        )
        main_container.bind(minimum_height=main_container.setter('height'))

        if not allies:
            no_allies_label = Label(
                text="У вас нет союзника",
                **STYLE_LABEL_HEADER,
                size_hint_y=None,
                height=dp(40)
            )
            main_container.add_widget(no_allies_label)
            scroll = ScrollView(size_hint=(1, 1))
            scroll.add_widget(main_container)
            return scroll

        ally_name = allies[0]

        # Заголовок с именем союзника
        ally_header = Label(
            text=f"Союзник: {ally_name}",
            **STYLE_LABEL_HEADER,
            size_hint_y=None,
            height=dp(50),
            halign='center'
        )
        ally_header.bind(size=ally_header.setter('text_size'))
        main_container.add_widget(ally_header)

        # Основной контейнер с двумя колонками
        columns_container = BoxLayout(
            orientation='horizontal',
            spacing=dp(20),
            size_hint=(1, None)  # Автоматическая ширина, фиксированная высота
        )

        # Левая колонка - экономическая помощь
        economic_column = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint=(0.5, None)  # 50% ширины контейнера
        )

        economic_header = Label(
            text="Экономическая помощь",
            **STYLE_LABEL_HEADER,
            size_hint_y=None,
            height=dp(40),
            halign='center'
        )
        economic_header.bind(size=economic_header.setter('text_size'))
        economic_column.add_widget(economic_header)

        resources = ['Кроны', 'Сырьё', 'Рабочие']
        for res in resources:
            btn_res = StyledButton(
                text=res,
                background_color=(0.2, 0.6, 0.8, 1) if res != "Сырьё" else (0.3, 0.7, 0.3, 1),
                **STYLE_BUTTON_ACTION,
                size_hint_y=None,
                height=dp(50)  # Фиксированная высота кнопок
            )
            btn_res.bind(on_release=lambda btn, r=res: self._on_resource_selected(ally_name, r))
            economic_column.add_widget(btn_res)

        economic_column.bind(minimum_height=economic_column.setter('height'))

        # Правая колонка - военная помощь
        military_column = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            size_hint=(0.5, None)  # 50% ширины контейнера
        )

        military_header = Label(
            text="Военная помощь",
            **STYLE_LABEL_HEADER,
            size_hint_y=None,
            height=dp(50),
            halign='center'
        )
        military_header.bind(size=military_header.setter('text_size'))
        military_column.add_widget(military_header)

        defense_btn = StyledButton(
            text="Защита",
            background_color=(0.3, 0.7, 0.3, 1),
            **STYLE_BUTTON_ACTION,
            size_hint_y=None,
            height=dp(50)
        )
        defense_btn.bind(on_release=lambda btn: self._on_action_wrapper('defense', ally_name, btn))

        attack_btn = StyledButton(
            text="Атака",
            background_color=(0.8, 0.3, 0.3, 1),
            **STYLE_BUTTON_DANGER,
            size_hint_y=None,
            height=dp(50)
        )
        attack_btn.bind(on_release=lambda btn: self._on_action_wrapper('attack', ally_name, btn))

        military_column.add_widget(defense_btn)
        military_column.add_widget(attack_btn)

        # Добавляем пустой виджет для выравнивания
        spacer = Widget(size_hint_y=None, height=dp(50))
        military_column.add_widget(spacer)

        military_column.bind(minimum_height=military_column.setter('height'))

        # Добавляем колонки в основной контейнер
        columns_container.add_widget(economic_column)
        columns_container.add_widget(military_column)

        columns_container.bind(minimum_height=columns_container.setter('height'))
        main_container.add_widget(columns_container)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(main_container)
        return scroll


    def _on_action_wrapper(self, action, ally, instance):
        self._on_action(action, ally)


    def _on_resource_selected(self, ally, resource):
        self._send_request(ally, resource)

    def _get_allies_from_db(self):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT faction1, faction2 FROM diplomacies "
            "WHERE (faction1=? OR faction2=?) AND relationship='союз'",
            (self.faction_name, self.faction_name)
        )
        allies = {
            r[1] if r[0] == self.faction_name else r[0]
            for r in cur.fetchall()
        }
        conn.close()
        return list(allies)

    def _on_action(self, action, ally):
        """
        Обработчик нажатия на кнопки "Защита" или "Атака"
        """
        self.progress_bar.opacity = 1
        self.progress_bar.value = 0
        self.status_label.text = f"Ожидание выбора города для {'защиты' if action == 'defense' else 'атаки'}..."

        # Инициализация переменных для отслеживания выбора города
        self.city_wait_start_time = time.time()
        self.city_last_name = ""
        self.city_selection_duration = 3  # Минимальное время для подтверждения выбора

        # Запуск проверки выбора города
        self.city_check_event = Clock.schedule_interval(
            lambda dt: self._check_city_selection(dt, action, ally), 0.2
        )

        # Запуск прогресс-бара
        self.progress_event = Clock.schedule_interval(
            lambda dt: self._update_progress_bar(dt), 0.05
        )

        # Таймер на 10 секунд для отмены выбора
        self.cancel_timer = Clock.schedule_once(
            lambda dt: self._cancel_selection(action, ally), 10
        )

        self.dismiss()

    def _cancel_selection(self, action, ally):
        """
        Отменяет выбор города, если время истекло
        """
        # Останавливаем проверку выбора города
        if hasattr(self, 'city_check_event'):
            Clock.unschedule(self.city_check_event)
        if hasattr(self, 'progress_event'):
            Clock.unschedule(self.progress_event)

        # Сбрасываем интерфейс
        self.progress_bar.opacity = 0
        self.status_label.text = "Город не выбран. Выбор отменён."

        # Оповещаем пользователя
        self._show_fullscreen_message("Выбор города отменён")

    def _check_city_selection(self, dt, action, ally):
        """
        Проверяет, был ли выбран город
        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT city_name FROM last_click")
        row = cur.fetchone()
        conn.close()

        if row and row[0]:
            current_city = row[0]

            # Если город только что выбран
            if not self.city_last_name:
                self.city_last_name = current_city
                self.city_wait_start_time = time.time()

            # Если город выбран и прошло достаточно времени для подтверждения
            elif current_city == self.city_last_name:
                if time.time() - self.city_wait_start_time > self.city_selection_duration:
                    if self._has_existing_action():
                        self.status_label.text = "Нельзя отправить более одного запроса за ход."
                    else:
                        self._finalize_city_selection(current_city, action, ally)
                    Clock.unschedule(self.city_check_event)
                    Clock.unschedule(self.progress_event)
                    if hasattr(self, 'cancel_timer'):
                        Clock.unschedule(self.cancel_timer)
        else:
            # Если город не выбран и прошло 10 секунд
            if time.time() - self.city_wait_start_time > 10:
                self._cancel_selection(action, ally)
                Clock.unschedule(self.city_check_event)
                Clock.unschedule(self.progress_event)

    def _update_progress_bar(self, dt):
        if self.progress_bar.value < 100:
            self.progress_bar.value += 2
        else:
            self.progress_bar.value = 100

    def _has_existing_action(self):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM queries")
        count = cur.fetchone()[0]
        conn.close()
        return count > 0


    def save_query_attack_to_db(self, attack_city):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            ("", "", attack_city, self.faction_name)
        )
        conn.commit()
        conn.close()

    def save_query_defense_to_db(self, defense_city):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            ("", defense_city, "", self.faction_name)
        )
        conn.commit()
        conn.close()

    def save_query_resources_to_db(self, resource):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            (resource, "", "", self.faction_name)
        )
        conn.commit()
        conn.close()

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _send_request(self, ally, resource):
        self.save_query_resources_to_db(resource)
        self.status_label.text = f"Запрос на перевод {resource} нам {ally} отправлен."

    def open_popup(self):
        super().open()