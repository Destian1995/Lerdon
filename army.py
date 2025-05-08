# army.py
from kivy.animation import Animation

from kivy.uix.carousel import Carousel
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp

from kivy.utils import get_color_from_hex

from economic import format_number

import sqlite3

from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'

PRIMARY_COLOR = get_color_from_hex('#2E7D32')
SECONDARY_COLOR = get_color_from_hex('#388E3C')
BACKGROUND_COLOR = get_color_from_hex('#212121')
TEXT_COLOR = get_color_from_hex('#FFFFFF')
INPUT_BACKGROUND = get_color_from_hex('#424242')

class ArmyButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0,0,0,0)
        self.color = TEXT_COLOR
        self.font_size = dp(18)
        self.bold = True
        self.size_hint = (1, None)
        self.height = dp(60)
        self.padding = (dp(20), dp(10))

        with self.canvas.before:
            Color(*PRIMARY_COLOR)
            self.rect = RoundedRectangle(
                radius=[dp(15)],
                pos=self.pos,
                size=self.size
            )

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            Animation(background_color=(*SECONDARY_COLOR, 1), d=0.1).start(self)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        Animation(background_color=(*PRIMARY_COLOR, 1), d=0.2).start(self)
        return super().on_touch_up(touch)

class ArmyCash:
    def __init__(self, faction, class_faction):
        """
        Инициализация класса ArmyCash.
        :param faction: Название фракции.
        :param class_faction: Экземпляр класса Faction (экономический модуль).
        """
        self.faction = faction
        self.class_faction = class_faction  # Экономический модуль
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.resources = self.load_resources()  # Загрузка начальных ресурсов

    def load_resources(self):
        """
        Загружает текущие ресурсы фракции из базы данных.
        """
        try:
            rows = self.load_data("resources", ["resource_type", "amount"], "faction = ?", (self.faction,))
            resources = {"Кроны": 0, "Рабочие": 0}
            for resource_type, amount in rows:
                if resource_type in resources:
                    resources[resource_type] = amount

            # Отладочный вывод: загруженные ресурсы
            print(f"[DEBUG] Загружены ресурсы для фракции '{self.faction}': {resources}")
            return resources
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке ресурсов: {e}")
            return {"Кроны": 0, "Рабочие": 0}

    def load_data(self, table, columns, condition=None, params=None):
        """
        Универсальный метод для загрузки данных из таблицы базы данных.
        """
        try:
            query = f"SELECT {', '.join(columns)} FROM {table}"
            if condition:
                query += f" WHERE {condition}"
            self.cursor.execute(query, params or ())
            result = self.cursor.fetchall()

            # Отладочный вывод: SQL-запрос и результат
            print(f"[DEBUG] SQL-запрос: {query}, параметры: {params}")
            print(f"[DEBUG] Результат запроса: {result}")

            return result
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке данных из таблицы {table}: {e}")
            return []

    def deduct_resources(self, crowns, workers):
        """
        Списывает ресурсы через экономический модуль.

        :param crowns: Количество крон для списания.
        :param workers: Количество рабочих для списания.
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
            self.class_faction.update_resource_now("Рабочие", current_workers - workers)

            return True

        except Exception as e:
            print(f"Ошибка при списании ресурсов: {e}")
            return False

    def hire_unit(self, unit_name, unit_cost, quantity, unit_stats, unit_image):
        """
        Нанимает юнит (оружие), если ресурсов достаточно.
        :param unit_name: Название юнита.
        :param unit_cost: Стоимость юнита в виде кортежа (кроны, рабочие).
        :param quantity: Количество нанимаемых юнитов.
        :param unit_stats: Характеристики юнита (должен быть словарем).
        :return: True, если найм успешен; False, если недостаточно ресурсов.
        """
        crowns, workers = unit_cost
        required_crowns = int(crowns) * int(quantity)
        required_workers = int(workers) * int(quantity)

        # Проверка наличия ресурсов
        if not self.deduct_resources(required_crowns, required_workers):
            self.show_message(
                title="Ошибка найма",
                message=f"Нанять юнитов невозможно: недостаточно ресурсов.\n"
                        f"Необходимые: {format_number(required_crowns)} крон и {format_number(required_workers)} рабочих."
            )
            return False

        # Проверка типа unit_stats
        if not isinstance(unit_stats, dict):
            print("[ERROR] unit_stats должен быть словарем!")
            return False

        # Добавление юнитов в базу данных
        self.add_or_update_army_unit(unit_name, quantity, unit_stats, unit_image)

        # Отображение сообщения об успехе
        self.show_message(
            title="Успех",
            message=f"{unit_name} нанят! \n"
                    f"Потрачено: {format_number(required_crowns)} крон и {format_number(required_workers)} рабочих."
        )
        return True

    def add_or_update_army_unit(self, unit_name, quantity, unit_stats, unit_image):
        """
        Добавляет или обновляет данные о юните в базе данных.
        """
        self.cursor.execute("""
            SELECT quantity, total_attack, total_defense, total_durability, unit_image
            FROM armies
            WHERE faction = ? AND unit_type = ?
        """, (self.faction, unit_name))
        result = self.cursor.fetchone()

        if result:
            # Если юнит уже существует, обновляем его данные
            current_quantity, total_attack, total_defense, total_durability, _ = result
            new_quantity = current_quantity + quantity
            self.cursor.execute("""
                UPDATE armies
                SET quantity = ?, total_attack = ?, total_defense = ?, total_durability = ?, unit_image = ?
                WHERE faction = ? AND unit_type = ?
            """, (
                new_quantity,
                total_attack + unit_stats["Урон"] * quantity,
                total_defense + unit_stats["Защита"] * quantity,
                total_durability + unit_stats["Живучесть"] * quantity,
                unit_image,  # Обновляем изображение
                self.faction,
                unit_name
            ))
        else:
            # Если юнит новый, добавляем его в базу
            self.cursor.execute("""
                INSERT INTO armies (faction, unit_type, quantity, total_attack, total_defense, total_durability, unit_class, unit_image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.faction,
                unit_name,
                quantity,
                unit_stats["Урон"] * quantity,
                unit_stats["Защита"] * quantity,
                unit_stats["Живучесть"] * quantity,
                unit_stats["Класс юнита"],
                unit_image  # Добавляем изображение
            ))

        self.conn.commit()

    def hire_weapons(self, weapon_name, unit_cost, quantity):
        """
        Обновляет или создает запись в таблице weapons.
        :param unit_cost: кортеж, содержащий стоимость оружия в кронах и рабочих.
        """
        crowns, workers = unit_cost
        required_crowns = int(crowns) * int(quantity)
        required_workers = int(workers) * int(quantity)


        # Проверка наличия ресурсов
        if not self.deduct_resources(required_crowns, required_workers):
            self.show_message(
                title="Ошибка найма",
                message=f"Нанять юнитов невозможно: недостаточно ресурсов.\n"
                        f"Необходимые: {format_number(required_crowns)} крон и {format_number(required_workers)} рабочих."
            )
            return False
        return True

    def update_weapon_in_db(self, faction, weapon_name, quantity, damage, koef):
        """
        Обновляет или создает запись в таблице weapons.
        :param faction: Название фракции.
        :param weapon_name: Название оружия.
        :param quantity: Количество единиц оружия.
        :param damage: Урон оружия.
        :param koef: Коэффициент преодоления ПВО.
        """
        try:
            # Проверяем, существует ли запись для данного оружия
            self.cursor.execute('''
                SELECT quantity
                FROM weapons
                WHERE faction = ? AND weapon_name = ?
            ''', (faction, weapon_name))
            result = self.cursor.fetchone()

            if result:
                # Если запись существует, обновляем количество
                current_quantity = result[0]
                new_quantity = current_quantity + quantity
                self.cursor.execute('''
                    UPDATE weapons
                    SET quantity = ?, damage = ?, koef = ?
                    WHERE faction = ? AND weapon_name = ?
                ''', (new_quantity, damage, koef, faction, weapon_name))
            else:
                # Если запись отсутствует, создаем новую
                self.cursor.execute('''
                    INSERT INTO weapons (faction, weapon_name, quantity, damage, koef)
                    VALUES (?, ?, ?, ?, ?)
                ''', (faction, weapon_name, quantity, damage, koef))

            self.conn.commit()
            print(f"[DEBUG] Данные оружия '{weapon_name}' успешно обновлены в таблице weapons.")

        except sqlite3.Error as e:
            print(f"Ошибка при обновлении таблицы weapons: {e}")

    def show_message(self, title, message):
        """
        Отображает всплывающее сообщение поверх всех окон.
        :param title: Заголовок сообщения.
        :param message: Текст сообщения.
        """
        # Создаем контент для всплывающего окна
        content_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        message_label = Label(
            text=message,
            color=(1, 1, 1, 1),  # Белый текст
            font_size=16,
            size_hint_y=None,
            height=100
        )
        close_button = Button(
            text="Закрыть",
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.6, 1, 1)  # Синий фон кнопки
        )

        # Добавляем виджеты в контент
        content_layout.add_widget(message_label)
        content_layout.add_widget(close_button)

        # Создаем Popup
        popup = Popup(
            title=title,
            content=content_layout,
            size_hint=(0.6, 0.4),  # Размер окна (60% ширины, 40% высоты)
            auto_dismiss=False  # Окно не закрывается автоматически при клике вне его
        )

        # Привязываем кнопку "Закрыть" к закрытию Popup
        close_button.bind(on_release=popup.dismiss)

        # Открываем Popup
        popup.open()


def load_unit_data(faction):
    """Загружает данные о юнитах для выбранной фракции из базы данных."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT unit_name, consumption, cost_money, cost_time, image_path, attack, defense, durability, unit_class
        FROM units WHERE faction = ?
    """, (faction,))
    rows = cursor.fetchall()
    conn.close()

    unit_data = {}
    for row in rows:
        unit_name, consumption, cost_money, cost_time, image_path, attack, defense, durability, unit_class = row
        unit_data[unit_name] = {
            "cost": [cost_money, cost_time],
            "image": image_path,
            "stats": {
                "Урон": attack,
                "Защита": defense,
                "Живучесть": durability,
                "Класс юнита": unit_class,
                "Потребление сырья": consumption
            }
        }
    return unit_data


def start_army_mode(faction, game_area, class_faction):
    army_hire = ArmyCash(faction, class_faction)

    # Определяем цвет фона в зависимости от фракции
    faction_colors = {
        "Аркадия": (0.2, 0.4, 0.9, 0.8),
        "Селестия": (0.2, 0.7, 0.3, 0.8),
        "Хиперион": (0.5, 0.2, 0.6, 0.8),
        "Этерия": (0, 0, 0, 0.8),
        "Халидон": (0.6, 0.5, 0.1, 0.8),
    }

    bg_color = faction_colors.get(faction, (0.15, 0.15, 0.15, 1))  # По умолчанию серый

    # Главный контейнер с разделением на левую и правую части
    main_box = BoxLayout(
        orientation='horizontal',
        size_hint=(1, 1),
        padding=dp(10),
        spacing=dp(5)
    )

    # Пустой левый контейнер (30% ширины) НЕ ТРОГАТЬ
    left_space = BoxLayout(size_hint=(0.3, 1))

    # Правый контейнер для карусели (70% ширины)
    right_container = BoxLayout(
        orientation='vertical',
        size_hint=(0.7, 1),
        padding=[dp(15), dp(25), dp(15), dp(25)]
    )

    # Настройка карусели с направлением вправо
    carousel = Carousel(
        direction='right',
        size_hint=(1, 0.9),
        loop=True,
        scroll_distance=100
    )

    unit_data = load_unit_data(faction)

    # Сортируем юнитов по классу (от 1 до N)
    sorted_units = sorted(
        unit_data.items(),
        key=lambda x: int(x[1]['stats']['Класс юнита'].split()[0])
    )

    # Добавляем юнитов в отсортированном порядке (от слабых к сильным)
    for unit_name, unit_info in sorted_units:
        # Слайд карусели
        slide = BoxLayout(
            orientation='vertical',
            size_hint=(0.85, 0.9),
            spacing=dp(10)
        )

        # Карточка юнита
        card = BoxLayout(
            orientation='vertical',
            size_hint=(1, 1),
            spacing=dp(8),
            padding=dp(20)
        )

        # Графические элементы для фона
        with card.canvas.before:
            # Тень
            Color(rgba=bg_color)
            shadow_rect = RoundedRectangle(
                size=card.size,
                radius=[dp(25)]
            )

            # Основной фон
            Color(rgba=(0.05, 0.05, 0.05, 0))
            rect = RoundedRectangle(
                size=card.size,
                radius=[dp(20)]
            )

        def update_bg(instance, rect=rect, shadow_rect=shadow_rect):
            rect.pos = instance.pos
            rect.size = instance.size
            shadow_rect.pos = (instance.x - dp(2), instance.y - dp(2))
            shadow_rect.size = instance.size

        card.bind(pos=update_bg, size=update_bg)

        # Заголовок
        header = BoxLayout(
            size_hint=(1, 0.12),
            orientation='horizontal',
            padding=dp(5)
        )

        title = Label(
            text=unit_name,
            font_size=set_font_size(0.03),  # Автоматический размер шрифта
            bold=True,
            color=TEXT_COLOR,
            halign='left',
            text_size=(None, None),
            size_hint_y=None,
            height='40sp'
        )
        header.add_widget(title)

        # Основное тело карточки
        body = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.6),  # Уменьшили высоту для места под стоимость
            spacing=dp(15)
        )

        # Контейнер для изображения
        img_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.5, 1),
            padding=[0, dp(10), 0, 0]
        )

        img = Image(
            source=unit_info['image'],
            size_hint=(1, 1),
            keep_ratio=True,
            allow_stretch=True,
            mipmap=True
        )
        img_container.add_widget(img)

        # Контейнер для характеристик
        stats_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.5, 1),
            spacing=dp(5)
        )

        main_stats = [
            ('Урон', unit_info['stats']['Урон'], '#FFFFFF'),
            ('Защита', unit_info['stats']['Защита'], '#FFFFFF'),
            ('Живучесть', unit_info['stats']['Живучесть'], '#FFFFFF'),
            ('Класс', unit_info['stats']['Класс юнита'], '#FFFFFF'),
            ('Потребление', unit_info['stats']['Потребление сырья'], '#FFFFFF')
        ]

        for name, value, color in main_stats:
            stat_line = BoxLayout(
                orientation='horizontal',
                size_hint=(1, None),
                height='30sp'
            )
            lbl_name = Label(
                text=f"[color={color}]{name}[/color]",
                markup=True,
                font_size=set_font_size(0.02),  # Автоматический размер
                halign='left',
                size_hint=(0.6, 1),
                text_size=(None, None)
            )
            lbl_value = Label(
                text=str(value),
                font_size=set_font_size(0.022),
                bold=True,
                color=TEXT_COLOR,
                size_hint=(0.4, 1),
                halign='right'
            )
            stat_line.add_widget(lbl_name)
            stat_line.add_widget(lbl_value)
            stats_container.add_widget(stat_line)

        body.add_widget(img_container)
        body.add_widget(stats_container)

        # Контейнер для стоимости (новый блок)
        cost_container = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.2),  # 20% высоты карточки
            spacing=dp(10),
            padding=[dp(15), 0, dp(15), 0]
        )

        # Лейбл "Цена" справа
        price_label = Label(
            text="Цена:  ",
            font_size=set_font_size(0.025),
            bold=True,
            color=TEXT_COLOR,
            halign='right',
            size_hint=(0.3, 1)
        )

        # Контейнер для значений стоимости
        cost_values = BoxLayout(
            orientation='vertical',
            size_hint=(0.7, 1),
            spacing=dp(5)
        )

        cost_money, cost_time = unit_info['cost']

        # Строка стоимости денег
        money_stat = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.5),
            spacing=dp(5)
        )
        money_icon = Label(
            text="[color=#FFFFFF]Кроны[/color]",  # Символ валюты
            markup=True,
            font_size=set_font_size(0.025),
            halign='left',
            size_hint=(0.2, 1)
        )
        money_value = Label(
            text=f"{cost_money}",
            font_size=set_font_size(0.025),
            bold=True,
            color=TEXT_COLOR,
            size_hint=(0.8, 1),
            halign='left'
        )
        money_stat.add_widget(money_icon)
        money_stat.add_widget(money_value)

        # Строка времени найма
        time_stat = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.5),
            spacing=dp(5)
        )
        time_icon = Label(
            text="[color=#FFFFFF]Рабочие[/color]",  # Символ времени
            markup=True,
            font_size=set_font_size(0.025),
            halign='left',
            size_hint=(0.2, 1)
        )
        time_value = Label(
            text=f"{cost_time}",
            font_size=set_font_size(0.025),
            bold=True,
            color=TEXT_COLOR,
            size_hint=(0.8, 1),
            halign='left'
        )
        time_stat.add_widget(time_icon)
        time_stat.add_widget(time_value)

        cost_values.add_widget(money_stat)
        cost_values.add_widget(time_stat)

        cost_container.add_widget(price_label)
        cost_container.add_widget(cost_values)

        # Панель управления
        control_panel = BoxLayout(
            size_hint=(1, 0.18),
            orientation='horizontal',
            spacing=dp(10),
            padding=[dp(5), dp(10), dp(5), dp(5)]
        )

        input_qty = TextInput(
            hint_text='Количество',
            input_filter='int',
            font_size=set_font_size(0.025),
            size_hint=(0.6, 1),
            background_color=INPUT_BACKGROUND,
            halign='center',
            multiline=False
        )

        btn_hire = Button(
            text='НАБРАТЬ',
            font_size=set_font_size(0.025),
            bold=True,
            background_color=PRIMARY_COLOR,
            color=TEXT_COLOR,
            size_hint=(0.4, 1)
        )

        btn_hire.bind(on_release=lambda instance, name=unit_name, cost=unit_info['cost'],
                                        input_box=input_qty, stats=unit_info['stats'], image=unit_info["image"]:
        broadcast_units(name, cost, input_box, army_hire, image, stats))

        control_panel.add_widget(input_qty)
        control_panel.add_widget(btn_hire)

        # Сборка карточки
        card.add_widget(header)
        card.add_widget(body)
        card.add_widget(cost_container)
        card.add_widget(control_panel)
        slide.add_widget(card)
        carousel.add_widget(slide)

    right_container.add_widget(carousel)
    main_box.add_widget(left_space)
    main_box.add_widget(right_container)

    # Добавляем FloatLayout для кнопки закрытия
    float_layout = FloatLayout(size_hint=(1, 1))
    float_layout.add_widget(main_box)

    # Кнопка закрытия
    close_button = Button(
        text="X",
        size_hint=(None, None),
        size=(dp(40), dp(40)),
        pos_hint={'top': 0.85, 'right': 0.86},
        background_color=(1, 0, 0, 1),  # Красный цвет
        color=(1, 1, 1, 1),  # Белый текст
        font_size=set_font_size(0.03),
        bold=True
    )
    close_button.bind(on_release=lambda instance: game_area.clear_widgets())  # Закрытие вкладки
    float_layout.add_widget(close_button)

    game_area.add_widget(float_layout)

def set_font_size(relative_size):
    """Вычисляет размер шрифта относительно размера окна"""
    from kivy.core.window import Window
    return Window.width * relative_size

def broadcast_units(unit_name, unit_cost, quantity_input, army_hire, image, unit_stats):
    try:
        quantity = int(quantity_input.text) if quantity_input.text else 0
        if quantity <= 0:
            raise ValueError("Количество должно быть положительным числом")

        # Вызываем метод найма с передачей всех необходимых параметров
        army_hire.hire_unit(
            unit_name=unit_name,
            unit_cost=unit_cost,
            quantity=quantity,
            unit_stats=unit_stats,
            unit_image=image
        )

    except ValueError as e:
        show_army_message(
            title="Ошибка",
            message=f"[color=#FF0000]{str(e) or 'Введите корректное число!'}[/color]"
        )

def show_army_message(title, message):
    popup = Popup(
        title=title,
        content=Label(
            text=message,
            markup=True,
            font_size=dp(18),
            color=TEXT_COLOR),
        size_hint=(None, None),
        size=(dp(300), dp(200)),
        background_color=BACKGROUND_COLOR)
    popup.open()


#---------------------------------------------------------------
class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.2, 0.6, 0.8, 1)  # Основной цвет кнопки
            self.rect = RoundedRectangle(radius=[20], size=self.size, pos=self.pos)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        # Фиксируем радиус закругления
        self.rect.radius = [20]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Сохраняем радиус при анимации
            self.rect.size = (self.size[0] - 5, self.size[1] - 5)
            self.rect.radius = [20]  # Форсируем обновление радиуса
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            self.rect.size = self.size
            self.rect.radius = [20]  # Форсируем обновление радиуса
        return super().on_touch_up(touch)