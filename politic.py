
import sqlite3

from kivy.animation import Animation
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from economic import format_number

import threading

from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'

# Глобальная блокировка для работы с БД
db_lock = threading.Lock()
from kivy.uix.behaviors import ButtonBehavior
from manage_friend import ManageFriend

translation_dict = {
    "Аркадия": "arkadia",
    "Селестия": "celestia",
    "Этерия": "eteria",
    "Хиперион": "giperion",
    "Халидон": "halidon",
}

# Словарь для перевода названий файлов в русскоязычные названия фракций
faction_names = {
    "arkadia_in_city": "Аркадия",
    "celestia_in_city": "Селестия",
    "eteria_in_city": "Этерия",
    "giperion_in_city": "Хиперион",
    "halidon_in_city": "Халидон"
}

faction_names_build = {
    "arkadia_buildings_city": "Аркадия",
    "celestia_buildings_city": "Селестия",
    "eteria_buildings_city": "Этерия",
    "giperion_buildings_city": "Хиперион",
    "halidon_buildings_city": "Халидон"
}

def transform_filename(file_path):
    path_parts = file_path.split('/')
    for i, part in enumerate(path_parts):
        for ru_name, en_name in translation_dict.items():
            if ru_name in part:
                path_parts[i] = part.replace(ru_name, en_name)
    return '/'.join(path_parts)


reverse_translation_dict = {v: k for k, v in translation_dict.items()}

def all_factions(cursor):
    """
    Выгружает список активных фракций из таблицы diplomacies.
    Возвращает уникальный список фракций, у которых статус в relationship не равен "уничтожена".
    :param cursor: Курсор для работы с базой данных
    :return: Список активных фракций
    """
    try:
        # Запрос для получения всех уникальных фракций, кроме тех, что имеют статус "уничтожена"
        query = """
            SELECT DISTINCT faction 
            FROM (
                SELECT faction1 AS faction, relationship FROM diplomacies
                UNION
                SELECT faction2 AS faction, relationship FROM diplomacies
            ) AS all_factions
            WHERE relationship != 'уничтожена'
        """
        cursor.execute(query)
        factions = [row[0] for row in cursor.fetchall()]
        return factions
    except sqlite3.Error as e:
        print(f"Ошибка при получении списка активных фракций: {e}")
        return []

# Функция для расчета базового размера шрифта
def calculate_font_size():
    """Рассчитывает базовый размер шрифта на основе высоты окна."""
    base_height = 720  # Базовая высота окна для нормального размера шрифта
    default_font_size = 16  # Базовый размер шрифта
    scale_factor = Window.height / base_height  # Коэффициент масштабирования
    return max(8, int(default_font_size * scale_factor))  # Минимальный размер шрифта — 8

def show_warning(message, color=(1, 0, 0, 1)):
    warning_popup = Popup(
        title="Внимание",
        content=Label(
            text=message,
            color=color,
            font_size=font_size
        ),
        size_hint=(0.5, 0.3)
    )
    warning_popup.open()

class PoliticalCash:
    def __init__(self, faction, class_faction):
        """
        Инициализация класса PoliticalCash.
        :param faction: Название фракции.
        :param class_faction: Экземпляр класса Faction (экономический модуль).
        """
        self.faction = faction
        self.class_faction = class_faction  # Экономический модуль
        self.resources = self.load_resources()  # Загрузка начальных ресурсов

    def load_resources(self):
        """
        Загружает текущие ресурсы фракции через экономический модуль.
        """
        try:
            resources = {
                "Кроны": self.class_faction.get_resource_now("Кроны"),
                "Рабочие": self.class_faction.get_resource_now("Рабочие")
            }
            print(f"[DEBUG] Загружены ресурсы для фракции '{self.faction}': {resources}")
            return resources
        except Exception as e:
            print(f"Ошибка при загрузке ресурсов: {e}")
            return {"Кроны": 0, "Рабочие": 0}

    def deduct_resources(self, crowns, workers=0):
        """
        Списывает ресурсы через экономический модуль.
        :param crowns: Количество крон для списания.
        :param workers: Количество рабочих для списания (по умолчанию 0).
        :return: True, если ресурсы успешно списаны; False, если недостаточно ресурсов.
        """
        try:
            # Проверяем доступность ресурсов через экономический модуль
            current_crowns = self.class_faction.get_resource_now("Кроны")
            current_workers = self.class_faction.get_resource_now("Рабочие")
            print(f"[DEBUG] Текущие ресурсы: Кроны={current_crowns}, Рабочие={current_workers}")

            if current_crowns < crowns or current_workers < workers:
                print("[DEBUG] Недостаточно ресурсов для списания.")
                return False

            # Списываем ресурсы через экономический модуль
            self.class_faction.update_resource_now("Кроны", current_crowns - crowns)
            if workers > 0:
                self.class_faction.update_resource_now("Рабочие", current_workers - workers)

            return True
        except Exception as e:
            print(f"Ошибка при списании ресурсов: {e}")
            return False



# Кастомная кнопка с анимациями и эффектами
class StyledButton(ButtonBehavior, BoxLayout):
    def __init__(self, text, font_size, button_color, text_color, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = font_size * 3  # Высота кнопки зависит от размера шрифта
        self.padding = [font_size // 2, font_size // 4]  # Отступы внутри кнопки
        self.normal_color = button_color
        self.hover_color = [c * 0.9 for c in button_color]  # Темнее при наведении
        self.pressed_color = [c * 0.8 for c in button_color]  # Еще темнее при нажатии
        self.current_color = self.normal_color

        with self.canvas.before:
            self.color = Color(*self.current_color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[font_size // 2])

        self.bind(pos=self.update_rect, size=self.update_rect)

        self.label = Label(
            text=text,
            font_size=font_size * 1.2,
            color=text_color,
            bold=True,
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))
        self.add_widget(self.label)

        self.bind(on_press=self.on_press_effect, on_release=self.on_release_effect)
        self.bind(on_touch_move=self.on_hover, on_touch_up=self.on_leave)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_press_effect(self, instance):
        """Эффект затемнения при нажатии"""
        anim = Animation(current_color=self.pressed_color, duration=0.1)
        anim.start(self)
        self.update_color()

    def on_release_effect(self, instance):
        """Возвращаем цвет после нажатия"""
        anim = Animation(current_color=self.normal_color, duration=0.1)
        anim.start(self)
        self.update_color()

    def on_hover(self, instance, touch):
        """Эффект при наведении"""
        if self.collide_point(*touch.pos):
            anim = Animation(current_color=self.hover_color, duration=0.1)
            anim.start(self)
            self.update_color()

    def on_leave(self, instance, touch):
        """Возвращаем цвет, если курсор ушел с кнопки"""
        if not self.collide_point(*touch.pos):
            anim = Animation(current_color=self.normal_color, duration=0.1)
            anim.start(self)
            self.update_color()

    def update_color(self):
        """Обновляет цвет фона"""
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.current_color)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[self.height // 4])


def show_new_agreement_window(faction, game_area, class_faction):
    """Создание красивого окна с кнопками"""
    game_area.clear_widgets()

    # Создаем модальное окно
    modal = ModalView(
        size_hint=(0.8, 0.8),
        pos_hint={'center_x': 0.5, 'center_y': 0.5},
        background_color=(0, 0, 0, 0)  # Прозрачный фон
    )

    # Основной контейнер для окна
    window = BoxLayout(
        orientation='vertical',
        padding=20,
        spacing=15,
        size_hint=(1, 1)
    )

    # Фон окна
    with window.canvas.before:
        Color(0.1, 0.1, 0.1, 1)  # Темный фон
        window.rect = RoundedRectangle(size=window.size, pos=window.pos, radius=[15])
    window.bind(pos=lambda obj, pos: setattr(window.rect, 'pos', pos),
                size=lambda obj, size: setattr(window.rect, 'size', size))

    # Заголовок
    title = Label(
        text="Новый договор",
        size_hint=(1, None),
        height=50,
        font_size=24,
        color=(1, 1, 1, 1),
        bold=True
    )

    # Список кнопок
    button_layout = BoxLayout(
        orientation='vertical',
        spacing=5,  # Уменьшили расстояние между кнопками
        size_hint=(1, None),  # Высота будет зависеть от содержимого
        height=0  # Начальная высота
    )
    button_layout.bind(minimum_height=button_layout.setter('height'))  # Автоматическая высота

    # Рассчитываем базовый размер шрифта
    font_size = calculate_font_size()

    # Цвета для кнопок
    default_button_color = (0.2, 0.6, 1, 1)  # Синий цвет
    default_text_color = (1, 1, 1, 1)  # Белый текст

    # Создаем кнопки для каждой категории
    categories = [
        ("Торговое соглашение", show_trade_agreement_form),
        ("Договор об культурном обмене", lambda *args: show_cultural_exchange_form(faction, game_area, class_faction)),
        ("Заключение мира", lambda *args: show_peace_form(faction)),
        ("Заключение альянса", lambda *args: show_alliance_form(faction, game_area, class_faction)),
        ("Объявление войны", lambda *args: show_declare_war_form(faction)),
    ]

    for category_name, callback in categories:
        button = StyledButton(
            text=category_name,
            font_size=font_size * 1.2,
            button_color=default_button_color,
            text_color=default_text_color
        )
        button.bind(on_press=lambda instance, cb=callback: cb(faction, game_area))
        button_layout.add_widget(button)

    # Кнопка "Вернуться"
    back_button = StyledButton(
        text="Вернуться",
        font_size=font_size * 1.2,
        button_color=(0.8, 0.2, 0.2, 1),  # Красный цвет
        text_color=default_text_color
    )
    back_button.bind(on_press=lambda x: modal.dismiss())

    # Добавляем всё в основное окно
    window.add_widget(title)
    scroll_view = ScrollView(size_hint=(1, 0.7))  # Добавляем ScrollView для кнопок
    scroll_view.add_widget(button_layout)
    window.add_widget(scroll_view)
    window.add_widget(back_button)

    modal.add_widget(window)
    modal.open()

# Обновленная функция для создания формы торгового соглашения
def show_trade_agreement_form(faction, game_area):
    """Окно формы для торгового соглашения"""
    # Рассчитываем базовый размер шрифта
    font_size = calculate_font_size()
    button_height = font_size * 3  # Увеличиваем высоту кнопок (в 3 раза от размера шрифта)
    input_height = font_size * 2.5  # Увеличиваем высоту полей ввода (в 2.5 раза от размера шрифта)
    padding = font_size // 2  # Отступы
    spacing = font_size // 4  # Промежутки между элементами
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Список всех фракций
    available_factions = all_factions(cursor)  # Получаем активные фракции
    available_factions = [f for f in available_factions if f != faction]  # Исключаем текущую фракцию

    # Создаем контент для Popup
    content = BoxLayout(
        orientation='vertical',
        padding=padding,
        spacing=spacing
    )

    # Заголовок
    title = Label(
        text="Торговое соглашение",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.5,  # Заголовок крупнее
        color=(1, 1, 1, 1),
        bold=True,
        halign='center'
    )
    content.add_widget(title)

    # Спиннеры и поля ввода
    factions_spinner = Spinner(
        text="С какой фракцией?",
        values=available_factions,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        background_normal=''
    )
    content.add_widget(factions_spinner)

    our_resource_spinner = Spinner(
        text="Наш ресурс",
        values=["Рабочие", "Сырье", "Кроны"],
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        background_normal=''
    )
    content.add_widget(our_resource_spinner)

    their_resource_spinner = Spinner(
        text="Их ресурс",
        values=["Рабочие", "Сырье", "Кроны"],
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        background_normal=''
    )
    content.add_widget(their_resource_spinner)

    our_percentage_input = TextInput(
        hint_text="Сумма отчислений с нашей стороны",
        multiline=False,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.1, 0.1, 0.1, 1),
        foreground_color=(1, 1, 1, 1)
    )
    content.add_widget(our_percentage_input)

    their_percentage_input = TextInput(
        hint_text="Сумма прихода с их стороны",
        multiline=False,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.1, 0.1, 0.1, 1),
        foreground_color=(1, 1, 1, 1)
    )
    content.add_widget(their_percentage_input)

    agreement_summary = TextInput(
        readonly=True,
        multiline=True,
        size_hint=(1, None),
        height=button_height * 2,
        font_size=font_size,
        background_color=(0.1, 0.1, 0.1, 1),
        foreground_color=(1, 1, 1, 1)
    )
    content.add_widget(agreement_summary)

    # Кнопки
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    generate_button = Button(
        text="Сформировать условия",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.2  # Увеличиваем размер текста на кнопках
    )

    send_button = Button(
        text="Отправить условия договора",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.2,
        opacity=0
    )

    def generate_agreement(instance):
        global their_amount, our_amount
        errors = []

        # Проверка выбора фракции
        if factions_spinner.text == "С какой фракцией?":
            errors.append("Выберите фракцию")

        # Проверка выбора ресурсов
        if our_resource_spinner.text == "Наш ресурс":
            errors.append("Выберите наш ресурс")
        if their_resource_spinner.text == "Их ресурс":
            errors.append("Выберите их ресурс")

        # Проверка вводимых сумм
        try:
            our_amount = int(our_percentage_input.text)
            their_amount = int(their_percentage_input.text)

            if our_amount <= 0:
                errors.append("Наша сумма должна быть > 0")
            if their_amount <= 0:
                errors.append("Их сумма должна быть > 0")
        except ValueError:
            errors.append("Введите корректные числа")

        if errors:
            agreement_summary.text = "\n".join(errors)
            return

        # Если нет ошибок, формируем соглашение
        agreement_summary.text = (
            f"Торговое соглашение с фракцией {factions_spinner.text}.\n"
            f"Инициатор: {faction}.\n"
            f"Наш ресурс: {our_resource_spinner.text} ({our_amount}).\n"
            f"Их ресурс: {their_resource_spinner.text} ({their_amount})."
        )
        send_button.opacity = 1

    def send_agreement(instance):
        global conn
        faction_selected = factions_spinner.text

        # Проверка выбранной фракции
        if faction_selected == "С какой фракцией?":
            show_warning("Пожалуйста, выберите фракцию!")
            return

        # Проверка числовых значений
        try:
            our_amount = int(our_percentage_input.text)
            their_amount = int(their_percentage_input.text)

            if our_amount <= 0 or their_amount <= 0:
                raise ValueError()
        except ValueError:
            show_warning("Введите корректные положительные числа!")
            return

        # Проверяем существующее соглашение
        if check_existing_agreement(faction, faction_selected):
            show_warning("Соглашение уже существует!")
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO trade_agreements 
                (initiator, target_faction, initiator_type_resource, 
                 target_type_resource, initiator_summ_resource, target_summ_resource)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                faction,
                faction_selected,
                our_resource_spinner.text,
                their_resource_spinner.text,
                our_amount,
                their_amount
            ))

            conn.commit()
            agreement_summary.text = (
                f"Условия договора отправлены фракции {faction_selected}.\n"
                f"Если его примут поставки придут через 1 ход"
            )

        except sqlite3.Error as e:
            show_warning(f"Ошибка базы данных: {e}")

        finally:
            if conn:
                conn.close()
    generate_button.bind(on_press=generate_agreement)
    send_button.bind(on_press=send_agreement)
    button_layout.add_widget(generate_button)
    button_layout.add_widget(send_button)
    content.add_widget(button_layout)

    back_button = Button(
        text="Назад",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.2
    )
    back_button.bind(on_press=lambda x: popup.dismiss())
    content.add_widget(back_button)

    popup = Popup(
        title="Торговое соглашение",
        content=content,
        size_hint=(0.7, 0.8),
        auto_dismiss=False
    )
    popup.open()


def check_existing_agreement(initiator, target):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM trade_agreements 
        WHERE (initiator = ? AND target_faction = ?)
           OR (initiator = ? AND target_faction = ?)
    """, (initiator, target, target, initiator))

    result = cursor.fetchone()
    conn.close()

    return result is not None

# Обработчик изменения размера окна
def on_window_resize(instance, width, height):
    """Обновляет интерфейс при изменении размера окна."""
    global font_size
    font_size = calculate_font_size()

def connect_to_db():
    """Подключение к базе данных."""
    return sqlite3.connect(db_path)


def show_cultural_exchange_form(faction, game_area, class_faction):
    """Окно формы для договора о культурном обмене."""
    font_size = calculate_font_size()
    button_height = font_size * 3
    input_height = font_size * 2.5
    padding = font_size // 2
    spacing = font_size // 4

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Список всех фракций
    available_factions = all_factions(cursor)  # Получаем активные фракции
    available_factions = [f for f in available_factions if f != faction]  # Исключаем текущую фракцию

    # Создаем контент для Popup
    content = BoxLayout(
        orientation='vertical',
        padding=padding,
        spacing=spacing
    )

    # Заголовок
    title = Label(
        text="Договор о культурном обмене",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.5,
        color=(1, 1, 1, 1),
        bold=True,
        halign='center'
    )
    content.add_widget(title)

    # Спиннер для выбора фракции
    factions_spinner = Spinner(
        text="С какой фракцией?",
        values=available_factions,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        background_normal=''
    )
    content.add_widget(factions_spinner)

    # Описание
    description_label = Label(
        text="Обмен культурными ценностями повышает доверие между фракциями (+7% к отношениям).\n"
             "Стоимость: от 100 тыс. крон.",
        size_hint=(1, None),
        height=font_size * 4,
        font_size=font_size,
        color=(1, 1, 1, 1),
        halign='center'
    )
    description_label.bind(size=description_label.setter('text_size'))
    content.add_widget(description_label)

    # Сообщения пользователю
    message_label = Label(
        text="",
        size_hint=(1, None),
        height=font_size * 2,
        font_size=font_size,
        color=(0, 1, 0, 1),
        halign='center'
    )
    content.add_widget(message_label)

    # Функция для вывода предупреждений
    def show_warning(text, color=(1, 0, 0, 1)):
        """Выводит предупреждение."""
        message_label.text = text
        message_label.color = color

    # Создаем экземпляр PoliticalCash
    political_cash = PoliticalCash(faction, class_faction)

    # Подключаемся к базе данных
    conn = connect_to_db()
    cursor = conn.cursor()

    # Получаем количество городов для каждой фракции
    cursor.execute("SELECT faction, COUNT(*) FROM cities GROUP BY faction")
    city_counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    # Функция для отправки предложения
    def send_proposal(instance):
        """Отправляет предложение, если фракция выбрана и хватает денег."""
        target_faction = factions_spinner.text
        if target_faction == "С какой фракцией?":
            show_warning("Пожалуйста, выберите фракцию!")
            return

        # Подключаемся к базе данных
        conn = connect_to_db()
        cursor = conn.cursor()

        try:
            # Получаем текущие отношения между фракциями
            cursor.execute(
                "SELECT relationship FROM relations WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND "
                "faction2 = ?)",
                (faction, target_faction, target_faction, faction)
            )
            relation_record = cursor.fetchone()

            if not relation_record:
                show_warning(f"Отношения между {faction} и {target_faction} не определены!")
                return

            current_relationship = int(relation_record[0])

            # Проверяем уровень отношений
            if current_relationship >= 90:
                show_warning(
                    f"Текущие отношения с {target_faction}: {current_relationship}\n"
                    "Отношения уже находятся на высоком уровне.",
                    color=(1, 0.6, 0, 1)  # Оранжевый цвет для предупреждения
                )
                return

            # Получаем количество городов целевой фракции
            cursor.execute("SELECT COUNT(*) FROM cities WHERE faction = ?", (target_faction,))
            target_city_count = cursor.fetchone()[0]

            # Рассчитываем стоимость
            cost = 100_000 + (50_000 * target_city_count)

            # Получаем текущий баланс крон игрока через PoliticalCash
            current_balance = political_cash.resources["Кроны"]

            if current_balance < cost:
                show_warning(f"Недостаточно средств, требуется {format_number(cost)} крон.")
                return

            # Списываем средства через PoliticalCash
            if not political_cash.deduct_resources(cost):
                show_warning("Мы недавно уже подписали один договор! Попробуйте позже")
                return

            # Обновляем отношения в таблице relations
            new_relationship = min(100, current_relationship + 7)
            cursor.execute(
                "UPDATE relations SET relationship = ? WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND "
                "faction2 = ?)",
                (new_relationship, faction, target_faction, target_faction, faction)
            )
            conn.commit()

            show_warning(
                f"Отношения с {target_faction} улучшены до {new_relationship}\n"
                f"Списано {format_number(cost)} крон",
                color=(0, 1, 0, 1)  # Зеленый цвет для успешного сообщения
            )

        except Exception as e:
            show_warning(f"Произошла ошибка: {e}")
        finally:
            conn.close()

    # Кнопки
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    send_button = Button(
        text="Отправить предложение",
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        color=(1, 1, 1, 1),
        size_hint=(0.5, None),
        height=button_height
    )
    send_button.bind(on_press=send_proposal)

    back_button = Button(
        text="Назад",
        font_size=font_size,
        background_color=(0.8, 0.2, 0.2, 1),
        color=(1, 1, 1, 1),
        size_hint=(0.5, None),
        height=button_height
    )

    popup = Popup(
        title="Культурный обмен",
        content=content,
        size_hint=(0.7, 0.5),
        auto_dismiss=False
    )
    back_button.bind(on_press=popup.dismiss)

    button_layout.add_widget(send_button)
    button_layout.add_widget(back_button)
    content.add_widget(button_layout)

    popup.open()





def calculate_peace_army_points(conn, faction):
    """
    Вычисляет общие очки армии для указанной фракции.
    :param conn: Подключение к базе данных.
    :param faction: Название фракции.
    :return: Общие очки армии.
    """
    # Коэффициенты для классов юнитов
    class_coefficients = {
        1: 1.3,
        2: 1.7,
        3: 2.0,
        4: 3.0
    }

    total_points = 0
    cursor = conn.cursor()

    try:
        # Шаг 1: JOIN-запрос для получения данных о юнитах и их фракции
        cursor.execute("""
            SELECT g.city_id, g.unit_name, g.unit_count, u.attack, u.defense, u.durability, u.unit_class
            FROM garrisons g
            JOIN units u ON g.unit_name = u.unit_name
            WHERE u.faction = ?
        """, (faction,))
        units_data = cursor.fetchall()

        # Шаг 2: Вычисление очков для каждого юнита
        for city_id, unit_name, unit_count, attack, defense, durability, unit_class in units_data:
            base_score = attack + defense + durability
            class_multiplier = class_coefficients.get(unit_class, 1.0)  # Если класс не найден, используем 1.0
            unit_score = base_score * class_multiplier

            # Умножаем на количество юнитов
            total_points += unit_score * unit_count

        return total_points

    except Exception as e:
        print(f"Ошибка при вычислении очков армии: {e}")
        return 0


def show_peace_form(player_faction):
    """Окно формы для предложения о заключении мира."""
    # Рассчитываем базовый размер шрифта
    font_size = calculate_font_size()
    button_height = font_size * 3  # Высота кнопок
    input_height = font_size * 2.5  # Высота полей ввода
    padding = font_size // 2  # Отступы
    spacing = font_size // 4  # Промежутки между элементами

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Получаем текущие отношения фракции из таблицы diplomacies
        cursor.execute(
            "SELECT faction2, relationship FROM diplomacies WHERE faction1 = ?",
            (player_faction,)
        )
        relations = {faction: status for faction, status in cursor.fetchall()}
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        active_factions = all_factions(cursor)  # Получаем активные фракции
        available_factions = [f for f in active_factions if relations.get(f) == "война"]  # Оставляем только воюющие фракции

        # Если нет доступных фракций для заключения мира
        if not available_factions:
            popup_content = BoxLayout(
                orientation='vertical',
                padding=padding,
                spacing=spacing
            )
            message_label = Label(
                text="Мы сейчас ни с кем не воюем",
                size_hint=(1, None),
                height=font_size * 2,
                font_size=font_size,
                color=(0, 1, 0, 1),  # Зеленый цвет
                halign='center'
            )
            popup_content.add_widget(message_label)

            close_button = Button(
                text="Закрыть",
                font_size=font_size,
                background_color=(0.8, 0.2, 0.2, 1),  # Красный цвет
                color=(1, 1, 1, 1),
                size_hint=(1, None),
                height=button_height
            )

            popup = Popup(
                title="Заключение мира",
                content=popup_content,
                size_hint=(0.7, 0.3),
                auto_dismiss=False
            )
            close_button.bind(on_press=popup.dismiss)
            popup_content.add_widget(close_button)
            popup.open()
            return

        # Создаем контент для Popup
        content = BoxLayout(
            orientation='vertical',
            padding=padding,
            spacing=spacing
        )

        # Заголовок
        title = Label(
            text="Предложение о заключении мира",
            size_hint=(1, None),
            height=button_height,
            font_size=font_size * 1.5,
            color=(1, 1, 1, 1),
            bold=True,
            halign='center'
        )
        content.add_widget(title)

        # Спиннер для выбора фракции
        factions_spinner = Spinner(
            text="С какой фракцией?",
            values=available_factions,
            size_hint=(1, None),
            height=input_height,
            font_size=font_size,
            background_color=(0.2, 0.6, 1, 1),
            background_normal=''
        )
        content.add_widget(factions_spinner)

        # Сообщения пользователю
        message_label = Label(
            text="",
            size_hint=(1, None),
            height=font_size * 2,
            font_size=font_size,
            color=(0, 1, 0, 1),  # Зеленый цвет по умолчанию
            halign='center'
        )
        content.add_widget(message_label)

        # Функция для вывода предупреждений
        def show_warning(text, color=(1, 0, 0, 1)):
            """Выводит предупреждение с указанным цветом."""
            message_label.text = text
            message_label.color = color

        # Функция для отправки предложения
        def send_proposal(instance):
            """Отправляет предложение о заключении мира."""
            target_faction = factions_spinner.text
            if target_faction == "С какой фракцией?":
                show_warning("Пожалуйста, выберите фракцию!", color=(1, 0, 0, 1))  # Красный цвет
                return

            # Вычисление очков армии для игрока и противника
            player_points = calculate_peace_army_points(conn, player_faction)
            enemy_points = calculate_peace_army_points(conn, target_faction)

            # Проверка на наличие армии у врага
            if player_points == 0 and enemy_points > 0:
                show_warning("Обойдешься. Сейчас я отыграюсь по полной.", color=(1, 0, 0, 1))
                return

            # Условие: если нет армий, заключаем мир
            if enemy_points == 0 and player_points == 0:
                response = "Мы согласны на мир! Нам пока и воевать то нечем..."
                cursor.execute(
                    "UPDATE diplomacies SET relationship = ? WHERE faction1 = ? AND faction2 = ?",
                    ("нейтралитет", player_faction, target_faction)
                )
                cursor.execute(
                    "UPDATE diplomacies SET relationship = ? WHERE faction1 = ? AND faction2 = ?",
                    ("нейтралитет", target_faction, player_faction)
                )
                conn.commit()
                show_warning(response, color=(0, 1, 0, 1))  # Зеленый цвет
                return

            # Вычисление процента превосходства
            if player_points > enemy_points:
                superiority_percentage = ((player_points - enemy_points) / enemy_points) * 100
                if superiority_percentage >= 70:
                    response = "А смысл нам сопротивляться? Все приплыли.."
                elif 30 <= superiority_percentage < 70:
                    response = "Нихера себе повоевали...."
                elif 20 <= superiority_percentage < 30:
                    response = "Что там случилось...такое.."
                elif 10 <= superiority_percentage < 20:
                    response = "По-моему мы что-то упустили"
                else:
                    response = "В следующий раз мы будем лучше готовы"

                # Меняем статус на "нейтралитет" в таблице diplomacies
                cursor.execute(
                    "UPDATE diplomacies SET relationship = ? WHERE faction1 = ? AND faction2 = ?",
                    ("нейтралитет", player_faction, target_faction)
                )
                cursor.execute(
                    "UPDATE diplomacies SET relationship = ? WHERE faction1 = ? AND faction2 = ?",
                    ("нейтралитет", target_faction, player_faction)
                )
                conn.commit()

                show_warning(response, color=(0, 1, 0, 1))  # Зеленый цвет
            elif player_points < enemy_points:
                inferiority_percentage = ((enemy_points - player_points) / player_points) * 100
                if inferiority_percentage <= 15:
                    response = "Почти то что надо, подкинь пару крон и договоримся"
                    show_warning(response, color=(1, 1, 0, 1))  # Желтый цвет
                else:
                    response = "Мы еще не закончили Вас бить"
                    show_warning(response, color=(1, 0, 0, 1))  # Красный цвет
            else:
                response = "Сейчас передохнем и в рыло дадим"
                show_warning(response, color=(1, 0, 0, 1))  # Красный цвет

        # Кнопки
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=button_height,
            spacing=font_size // 2
        )

        # Цвета для кнопок
        default_button_color = (0.2, 0.6, 1, 1)  # Синий цвет
        default_text_color = (1, 1, 1, 1)  # Белый текст
        send_button = Button(
            text="Отправить предложение",
            font_size=font_size,
            background_color=default_button_color,
            color=default_text_color,
            size_hint=(0.5, None),
            height=button_height
        )
        send_button.bind(on_press=send_proposal)
        back_button = Button(
            text="Назад",
            font_size=font_size,
            background_color=(0.8, 0.2, 0.2, 1),  # Красный цвет
            color=default_text_color,
            size_hint=(0.5, None),
            height=button_height
        )

        # Создаем и открываем Popup
        popup = Popup(
            title="Заключение мира",
            content=content,
            size_hint=(0.7, 0.5),
            auto_dismiss=False
        )
        back_button.bind(on_press=popup.dismiss)

        button_layout.add_widget(send_button)
        button_layout.add_widget(back_button)
        content.add_widget(button_layout)

        popup.open()

    except Exception as e:
        print(f"Ошибка при работе с дипломатией: {e}")


# Словарь фраз для каждой фракции
alliance_phrases = {
    "Селестия": "Мы Вас прикроем, от огня врагов!",
    "Аркадия": "Светлого неба!",
    "Этерия": "Вместе мы непобедимы!",
    "Халидон": "Мудрость в том чтобы не допустить войны. В любом случае мы с Вами",
    "Хиперион": "Пора выбить кому то зубы. Так. На всякий случай"
}


def show_alliance_form(faction, game_area, class_faction):
    """Окно формы для предложения о создании альянса."""
    # Рассчитываем базовый размер шрифта
    font_size = calculate_font_size()
    button_height = font_size * 3  # Высота кнопок
    input_height = font_size * 2.5  # Высота полей ввода
    padding = font_size // 2  # Отступы
    spacing = font_size // 4  # Промежутки между элементами

    # Подключение к базе данных
    conn = sqlite3.connect(db_path)  # Замените на путь к вашей базе данных
    cursor = conn.cursor()

    # Проверка существования фракции в таблицах
    cursor.execute("SELECT COUNT(*) FROM diplomacies WHERE faction1 = ? OR faction2 = ?", (faction, faction))
    if cursor.fetchone()[0] == 0:
        print(f"Ошибка: Фракция '{faction}' не найдена в таблице 'diplomacies'.")
        conn.close()
        return

    cursor.execute("SELECT COUNT(*) FROM relations WHERE faction1 = ? OR faction2 = ?", (faction, faction))
    if cursor.fetchone()[0] == 0:
        print(f"Ошибка: Фракция '{faction}' не найдена в таблице 'relations'.")
        conn.close()
        return

    # Получение текущих отношений фракции из таблицы relations
    cursor.execute("""
        SELECT faction1, faction2, relationship 
        FROM relations 
        WHERE faction1 = ? OR faction2 = ?
    """, (faction, faction))
    relations_data = {row[1] if row[0] == faction else row[0]: row[2] for row in cursor.fetchall()}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Список всех фракций
    available_factions = all_factions(cursor)  # Получаем активные фракции
    available_factions = [f for f in available_factions if f != faction]  # Исключаем текущую фракцию

    # Создаем контент для Popup
    content = BoxLayout(
        orientation='vertical',
        padding=padding,
        spacing=spacing
    )

    # Заголовок
    title = Label(
        text="Предложение о создании альянса",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.5,
        color=(1, 1, 1, 1),
        bold=True,
        halign='center'
    )
    content.add_widget(title)

    # Спиннер для выбора фракции
    factions_spinner = Spinner(
        text="С какой фракцией?",
        values=available_factions,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        background_normal=''
    )
    content.add_widget(factions_spinner)

    # Описание
    description_label = Label(
        text="Создание альянса возможно только при высоком уровне доверия (>90).\n"
             "Уровень отношений влияет на возможность заключения союза.",
        size_hint=(1, None),
        height=font_size * 4,  # Высота зависит от количества строк
        font_size=font_size,
        color=(1, 1, 1, 1),
        halign='center'
    )
    description_label.bind(size=description_label.setter('text_size'))
    content.add_widget(description_label)

    # Сообщения пользователю
    message_label = Label(
        text="",
        size_hint=(1, None),
        height=font_size * 2,
        font_size=font_size,
        color=(0, 1, 0, 1),
        halign='center'
    )
    content.add_widget(message_label)

    # Функция для вывода предупреждений
    def show_warning(text, color=(1, 0, 0, 1)):
        """Выводит предупреждение."""
        message_label.text = text
        message_label.color = color

    # Функция для отправки предложения
    def send_proposal(instance):
        """Отправляет предложение о создании альянса."""
        target_faction = factions_spinner.text
        if target_faction == "С какой фракцией?":
            show_warning("Пожалуйста, выберите фракцию!")
            return

        # Проверяем уровень отношений
        relation_level = int(relations_data.get(target_faction, 0))

        # Проверяем наличие существующего союза у текущей фракции
        cursor.execute("""
            SELECT COUNT(*) FROM diplomacies 
            WHERE (faction1 = ? OR faction2 = ?) AND relationship = 'союз'
        """, (faction, faction))
        existing_alliance_count = cursor.fetchone()[0]

        if existing_alliance_count > 0:
            show_warning(
                "У вашей фракции уже есть действующий союз!",
                color=(1, 0, 0, 1)  # Красный цвет
            )
            return

        # Получаем количество городов целевой фракции
        cursor.execute("SELECT COUNT(*) FROM cities WHERE faction = ?", (target_faction,))
        target_city_count = cursor.fetchone()[0]

        # Рассчитываем стоимость альянса
        alliance_cost = 1_000_000 + (150_000 * target_city_count)

        # Получаем текущий баланс фракции
        political_cash = PoliticalCash(faction, class_faction)
        current_balance = political_cash.resources["Кроны"]

        # Проверяем достаточно ли средств
        if current_balance < alliance_cost:
            show_warning(
                f"Недостаточно средств для заключения альянса! "
                f"Требуется {format_number(alliance_cost)} крон.",
                color=(1, 0, 0, 1)  # Красный цвет
            )
            return

        # Проверяем уровень отношений
        if relation_level >= 90:
            # Списываем средства
            if not political_cash.deduct_resources(alliance_cost):
                show_warning("Ошибка при списании средств!")
                return

            # Меняем статус отношений на "союз"
            cursor.execute("""
                UPDATE diplomacies 
                SET relationship = 'союз' 
                WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
            """, (faction, target_faction, target_faction, faction))
            conn.commit()

            # Выводим сообщение об успешном заключении альянса
            alliance_phrase = alliance_phrases.get(target_faction, "Союз заключен!")
            show_warning(
                f"{alliance_phrase}\n"
                f"Списано {format_number(alliance_cost)} крон",
                color=(0, 1, 0, 1)  # Зеленый цвет
            )
        elif 75 <= relation_level < 90:
            show_warning("Друг. Мы должны сильнее доверять друг другу, тогда союз будет возможен.")
        elif 50 <= relation_level < 75:
            show_warning("Приятель. Пока сложно о чем-то конкретном говорить, давай лучше поближе узнаем друг друга.")
        elif 30 <= relation_level < 50:
            show_warning("Не сказал бы что в данный момент нас интересуют подобные предложения.")
        elif 15 <= relation_level < 30:
            show_warning("Да я лучше башку в осиное гнездо засуну чем вообще буду Вам отвечать.")
        else:
            show_warning("Вы там еще не сдохли? Ну ничего, мы это исправим.")

    # Кнопки
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    # Цвета для кнопок
    default_button_color = (0.2, 0.6, 1, 1)  # Синий цвет
    default_text_color = (1, 1, 1, 1)  # Белый текст
    send_button = Button(
        text="Отправить предложение",
        font_size=font_size,
        background_color=default_button_color,
        color=default_text_color,
        size_hint=(0.5, None),
        height=button_height
    )
    send_button.bind(on_press=send_proposal)
    back_button = Button(
        text="Назад",
        font_size=font_size,
        background_color=(0.8, 0.2, 0.2, 1),  # Красный цвет
        color=default_text_color,
        size_hint=(0.5, None),
        height=button_height
    )

    def close_connection(*args):
        conn.close()

    # Создаем и открываем Popup
    popup = Popup(
        title="Создание альянса",
        content=content,
        size_hint=(0.7, 0.5),
        auto_dismiss=False
    )
    back_button.bind(on_press=popup.dismiss)
    popup.bind(on_dismiss=close_connection)  # Привязываем функцию close_connection к событию закрытия popup

    button_layout.add_widget(send_button)
    button_layout.add_widget(back_button)
    content.add_widget(button_layout)

    popup.open()


from kivy.uix.popup import Popup

def show_declare_war_form(faction):
    """Окно формы для объявления войны."""
    # Рассчитываем базовый размер шрифта
    font_size = calculate_font_size()
    button_height = font_size * 3  # Высота кнопок
    input_height = font_size * 2.5  # Высота полей ввода
    padding = font_size // 2  # Отступы
    spacing = font_size // 4  # Промежутки между элементами

    # Подключение к базе данных через контекстный менеджер
    try:
        with sqlite3.connect(db_path) as conn:  # Замените на путь к вашей базе данных
            cursor = conn.cursor()

            # Проверка текущего хода
            cursor.execute("SELECT turn_count FROM turn")
            turn_result = cursor.fetchone()
            if turn_result is None:
                show_popup_message("Ошибка", "Таблица 'turn' пуста или отсутствует.")
                return

            current_turn = turn_result[0]
            if current_turn < 16:
                show_popup_message("Слишком рано", "Атаковать другие фракции можно только после 16 хода.")
                return

            # Получение списка активных фракций
            active_factions = all_factions(cursor)  # Используем функцию all_factions
            if faction not in active_factions:
                show_popup_message("Ошибка", f"Фракция '{faction}' не найдена среди активных фракций.")
                return

            # Получение текущих отношений фракции
            cursor.execute("""
                SELECT faction1, faction2, relationship 
                FROM diplomacies 
                WHERE faction1 = ? OR faction2 = ?
            """, (faction, faction))
            relations = {}
            for row in cursor.fetchall():
                other_faction = row[1] if row[0] == faction else row[0]
                relations[other_faction] = row[2]

            # Фильтрация стран, которым можно объявить войну (не "война")
            available_targets = [
                country for country, status in relations.items()
                if status != "война" and country in active_factions  # Только активные фракции
            ]
            if not available_targets:
                show_popup_message("Нет целей", "Нет доступных целей для объявления войны.")
                return

    except Exception as e:
        show_popup_message("Ошибка", f"Произошла ошибка при работе с базой данных: {e}")
        return

    # Уникальные фразы для каждой фракции
    faction_phrases = {
        "Селестия": "Вы нарываетесь на драку? Я к Вашим услугам!",
        "Аркадия": "Тебя давно по голове били? Сейчас исправим",
        "Этерия": "Вы слишком самонадеяны, Вам это аукнется",
        "Халидон": "Пуская пустыня поглодит Вас",
        "Хиперион": "Я сейчас кому-то в лицо плюну"
    }

    # Создаем контент для Popup
    content = BoxLayout(
        orientation='vertical',
        padding=padding,
        spacing=spacing
    )

    # Заголовок
    title = Label(
        text="Объявление войны",
        size_hint=(1, None),
        height=button_height,
        font_size=font_size * 1.5,
        color=(1, 1, 1, 1),
        bold=True,
        halign='center'
    )
    content.add_widget(title)

    # Спиннер для выбора фракции
    factions_spinner = Spinner(
        text="Выберите цель",
        values=available_targets,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        background_normal=''
    )
    content.add_widget(factions_spinner)

    # Сообщения пользователю
    message_label = Label(
        text="",
        size_hint=(1, None),
        height=font_size * 2,
        font_size=font_size,
        color=(0, 1, 0, 1),
        halign='center'
    )
    content.add_widget(message_label)

    # Функция для вывода предупреждений
    def show_warning(text, color=(1, 0, 0, 1)):
        """Выводит предупреждение."""
        message_label.text = text
        message_label.color = color

    # Функция для объявления войны
    def declare_war(instance):
        """Объявляет войну выбранной фракции."""
        target_faction = factions_spinner.text
        if target_faction == "Выберите цель":
            show_warning("Пожалуйста, выберите цель!")
            return

        try:
            # Подключение к базе данных
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Обновление статуса отношений в таблице diplomacies
                cursor.execute("""
                    UPDATE diplomacies 
                    SET relationship = 'война' 
                    WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
                """, (faction, target_faction, target_faction, faction))

                # Обнуление отношений в таблице relations
                cursor.execute("""
                    UPDATE relations 
                    SET relationship = 0 
                    WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
                """, (faction, target_faction, target_faction, faction))

                # Сохраняем изменения в базе данных
                conn.commit()

            # Вывод сообщения об успешном объявлении войны
            phrase = faction_phrases.get(target_faction, f"Война объявлена против {target_faction}!")
            show_warning(phrase, color=(1, 0, 0, 1))  # Красный текст

        except Exception as e:
            show_popup_message("Ошибка", f"Произошла ошибка при объявлении войны: {e}")

    # Кнопки
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    # Цвета для кнопок
    default_button_color = (0.2, 0.6, 1, 1)  # Синий цвет
    default_text_color = (1, 1, 1, 1)  # Белый текст

    declare_button = Button(
        text="Объявить войну",
        font_size=font_size,
        background_color=default_button_color,
        color=default_text_color,
        size_hint=(0.5, None),
        height=button_height
    )
    declare_button.bind(on_press=declare_war)

    back_button = Button(
        text="Назад",
        font_size=font_size,
        background_color=(0.8, 0.2, 0.2, 1),  # Красный цвет
        color=default_text_color,
        size_hint=(0.5, None),
        height=button_height
    )

    # Создаем и открываем Popup
    popup = Popup(
        title="Объявление войны",
        content=content,
        size_hint=(0.7, 0.5),
        auto_dismiss=False
    )

    # Привязываем кнопку "Назад" к закрытию Popup
    back_button.bind(on_press=popup.dismiss)

    # Добавляем кнопки в макет
    button_layout.add_widget(declare_button)
    button_layout.add_widget(back_button)
    content.add_widget(button_layout)

    # Открываем Popup
    popup.open()


def show_popup_message(title, message):
    """
    Показывает всплывающее окно с заданным заголовком и сообщением.

    :param title: Заголовок окна.
    :param message: Текст сообщения.
    """
    popup_content = BoxLayout(orientation='vertical', padding=10, spacing=10)
    popup_content.add_widget(Label(text=message, color=(1, 1, 1, 1), halign='center'))
    close_button = Button(text="Закрыть", size_hint=(1, 0.3))
    popup = Popup(title=title, content=popup_content, size_hint=(0.6, 0.4), auto_dismiss=False)
    close_button.bind(on_press=popup.dismiss)
    popup_content.add_widget(close_button)
    popup.open()




#-------------------------------------

def calculate_army_strength():
    """Рассчитывает силу армий для каждой фракции."""
    class_coefficients = {
        "1": 1.3,  # Класс 1: базовые юниты
        "2": 1.7,  # Класс 2: улучшенные юниты
        "3": 2.0,  # Класс 3: элитные юниты
        "4": 3.0   # Класс 4: легендарные юниты
    }

    army_strength = {}

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Получаем все юниты из таблицы garrisons и их характеристики из таблицы units
            cursor.execute("""
                SELECT g.unit_name, g.unit_count, u.faction, u.attack, u.defense, u.durability, u.unit_class 
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
            """)
            garrison_data = cursor.fetchall()

            # Рассчитываем силу армии для каждой фракции
            for row in garrison_data:
                unit_name, unit_count, faction, attack, defense, durability, unit_class = row

                if not faction:
                    continue

                # Коэффициент класса
                coefficient = class_coefficients.get(unit_class, 1.0)

                # Рассчитываем силу юнита
                unit_strength = (attack * coefficient) + defense + durability

                # Умножаем на количество юнитов
                total_strength = unit_strength * unit_count

                # Добавляем к общей силе фракции
                if faction not in army_strength:
                    army_strength[faction] = 0
                army_strength[faction] += total_strength

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return {}

    # Возвращаем два словаря: один с числовыми значениями, другой с отформатированными строками
    formatted_army_strength = {faction: format_number(strength) for faction, strength in army_strength.items()}
    return army_strength, formatted_army_strength


def create_army_rating_table():
    """Создает таблицу рейтинга армий на основе силы войск."""
    # Получаем числовые и отформатированные значения силы армий
    army_strength, formatted_army_strength = calculate_army_strength()

    if not army_strength:
        return GridLayout()

    max_strength = max(army_strength.values(), default=1)

    layout = GridLayout(cols=3, size_hint_y=None, spacing=5, padding=10)
    layout.bind(minimum_height=layout.setter('height'))

    def add_header_with_background(text):
        header = Label(
            text=text,
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=40
        )
        with header.canvas.before:
            Color(0.2, 0.6, 1, 1)  # Синий фон
            header.rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(
            pos=lambda _, value: setattr(header.rect, 'pos', value),
            size=lambda _, value: setattr(header.rect, 'size', value)
        )
        return header

    layout.add_widget(add_header_with_background("Страна"))
    layout.add_widget(add_header_with_background("Рейтинг"))
    layout.add_widget(add_header_with_background("Мощь"))

    rank_colors = {
        0: (1, 1, 1, 1),       # Белый (1-й)
        1: (0, 0.8, 0.8, 1),   # Бирюзовый (2-й)
        2: (0, 1, 0, 1),       # Зеленый (3-й)
        3: (1, 1, 0, 1),       # Желтый (4-й)
        4: (1, 0, 0, 1)        # Красный (5-й)
    }

    sorted_factions = sorted(
        army_strength.items(),
        key=lambda x: x[1],  # Сортируем по числовым значениям
        reverse=True
    )
    for rank, (faction, strength) in enumerate(sorted_factions):
        rating = (strength / max_strength) * 100 if max_strength > 0 else 0
        russian_name = faction_names.get(faction, faction)
        row_color = rank_colors.get(rank, (0.5, 0.5, 0.5, 1))

        # Отображаем отформатированное значение силы армии
        formatted_strength = formatted_army_strength[faction]

        layout.add_widget(Label(text=russian_name, color=row_color, size_hint_y=None, height=40))
        layout.add_widget(Label(text=f"{rating:.2f}%", color=row_color, size_hint_y=None, height=40))
        layout.add_widget(Label(text=formatted_strength, color=row_color, size_hint_y=None, height=40))

    return layout


def show_ratings_popup():
    """Открывает всплывающее окно с рейтингом армий."""
    # Создаем таблицу рейтинга армий
    table_layout = create_army_rating_table()

    # Оборачиваем таблицу в ScrollView
    scroll_view = ScrollView(size_hint=(1, 1))
    scroll_view.add_widget(table_layout)

    # Создаем всплывающее окно
    popup = Popup(
        title="Рейтинг армий",
        content=scroll_view,
        size_hint=(0.8, 0.8),
        auto_dismiss=True
    )
    popup.open()


#------------------------------------------------------------------
def start_politic_mode(faction, game_area, class_faction):
    """Инициализация политического режима для выбранной фракции"""
    # основное окно политических кнопок
    politics_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, 0.1),
        pos_hint={'x': 0, 'y': 0},
        spacing=10,
        padding=10
    )

    # создаём Popup заранее
    manage_friend_popup = ManageFriend(faction, game_area)

    def styled_btn(text, callback):
        btn = Button(
            text=text,
            size_hint_x=0.33,
            size_hint_y=None,
            height=50,
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size=16,
            bold=True
        )
        # фон кнопки
        with btn.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn._rect = Rectangle(pos=btn.pos, size=btn.size)
        btn.bind(pos=lambda inst, val: setattr(inst._rect, 'pos', inst.pos))
        btn.bind(size=lambda inst, val: setattr(inst._rect, 'size', inst.size))
        btn.bind(on_release=callback)
        return btn

    # кнопки политических действий
    btn_new = styled_btn(
        "Новый договор",
        lambda btn: show_new_agreement_window(faction, game_area, class_faction)
    )
    btn_allies = styled_btn(
        "Союзник",
        lambda btn: manage_friend_popup.open_popup()
    )
    btn_army = styled_btn(
        "Сила армий",
        lambda btn: show_ratings_popup()
    )

    # добавляем в layout
    politics_layout.add_widget(btn_new)
    politics_layout.add_widget(btn_allies)
    politics_layout.add_widget(btn_army)
    game_area.add_widget(politics_layout)
