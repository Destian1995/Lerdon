
from kivy.core.window import Window
from kivy.graphics import Rectangle, Color
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider

from kivy.uix.image import Image as KivyImage
from kivy.uix.textinput import TextInput

from fight import fight
from economic import format_number
import sqlite3
from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'
# Установка мягких цветов для фона
Window.clearcolor = (0.95, 0.95, 0.95, 1)  # Светло-серый фон


# format_number(unit_count)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class FortressInfoPopup(Popup):
    def __init__(self, ai_fraction, city_coords, player_fraction, **kwargs):
        super(FortressInfoPopup, self).__init__(**kwargs)

        # Создаем подключение к БД
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.cursor = self.conn.cursor()
        self.ai_fraction = ai_fraction
        self.city_name = ''
        self.city_coords = list(city_coords)
        self.size_hint = (0.8, 0.8)
        self.player_fraction = player_fraction
        self.file_path2 = None
        self.file_path1 = None
        self.city_coords = city_coords  # Это кортеж (x, y)
        self.current_popup = None  # Ссылка на текущее всплывающее окно

        # Преобразуем координаты в строку для сравнения с БД
        coords_str = f"[{self.city_coords[0]}, {self.city_coords[1]}]"

        # Получаем информацию о городе из таблицы cities
        self.cursor.execute("""
            SELECT name FROM cities 
            WHERE coordinates = ?
        """, (coords_str,))

        city_data = self.cursor.fetchone()
        if city_data:
            self.city_name = city_data[0]
        else:
            print(f"Город с координатами {self.city_coords} не найден в базе данных")
            return

        self.title = f"Информация о поселении {self.city_name}"
        self.create_ui()

    def create_ui(self):
        """
        Создает масштабируемый пользовательский интерфейс.
        """
        # Базовые параметры для масштабирования
        screen_width, screen_height = Window.size
        scale_factor = screen_width / 360  # Масштабный коэффициент (360 — базовая ширина экрана)

        base_font_size = 8  # Базовый размер шрифта
        base_padding = 7  # Базовый отступ
        base_spacing = 7  # Базовое расстояние между виджетами
        base_button_height = 20  # Базовая высота кнопок

        font_size = int(base_font_size * scale_factor)
        padding = int(base_padding * scale_factor)
        spacing = int(base_spacing * scale_factor)
        button_height = int(base_button_height * scale_factor)

        # Главный макет
        main_layout = BoxLayout(orientation='vertical', padding=padding, spacing=spacing)

        # Верхняя часть: Гарнизон и здания
        columns_layout = GridLayout(cols=2, spacing=spacing, size_hint_y=0.7)

        # Левая колонка: Гарнизон
        troops_column = BoxLayout(orientation='vertical', spacing=spacing)
        troops_label = Label(
            text="Гарнизон",
            font_size=f'{font_size*1.2}sp',
            bold=True,
            size_hint_y=None,
            height=int(30 * scale_factor),
            color=(1, 1, 1, 1)  # Черный текст
        )
        troops_column.add_widget(troops_label)

        self.attacking_units_list = ScrollView(size_hint=(1, 1))
        self.attacking_units_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=spacing)
        self.attacking_units_box.bind(minimum_height=self.attacking_units_box.setter('height'))
        self.attacking_units_list.add_widget(self.attacking_units_box)
        troops_column.add_widget(self.attacking_units_list)
        columns_layout.add_widget(troops_column)

        # Правая колонка: Здания
        buildings_column = BoxLayout(orientation='vertical', spacing=spacing)
        buildings_label = Label(
            text="Здания",
            font_size=f'{font_size*1.2}sp',
            bold=True,
            size_hint_y=None,
            height=int(30 * scale_factor),
            color=(1, 1, 1, 1)  # Черный текст
        )
        buildings_column.add_widget(buildings_label)

        self.buildings_list = ScrollView(size_hint=(1, 1))
        self.buildings_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=spacing)
        self.buildings_box.bind(minimum_height=self.buildings_box.setter('height'))
        self.buildings_list.add_widget(self.buildings_box)
        buildings_column.add_widget(self.buildings_list)
        columns_layout.add_widget(buildings_column)

        main_layout.add_widget(columns_layout)

        # Нижняя часть: Кнопки действий
        button_layout = GridLayout(cols=3, size_hint_y=None, height=button_height, spacing=spacing)

        # Кнопка "Ввести войска"
        send_troops_button = Button(
            text="Ввести войска",
            font_size=f'{font_size}sp',
            size_hint_y=None,
            height=button_height,
            background_color=(0.6, 0.8, 0.6, 1)
        )
        send_troops_button.bind(on_press=self.select_troop_type)
        button_layout.add_widget(send_troops_button)

        # Кнопка "Разместить армию"
        place_army_button = Button(
            text="Разместить армию",
            font_size=f'{font_size}sp',
            size_hint_y=None,
            height=button_height,
            background_color=(0.6, 0.6, 0.8, 1)
        )
        place_army_button.bind(on_press=self.place_army)
        button_layout.add_widget(place_army_button)

        main_layout.add_widget(button_layout)

        # Кнопка "Закрыть"
        close_button = Button(
            text="Закрыть",
            font_size=f'{font_size}sp',
            size_hint_y=None,
            height=button_height,
            background_color=(0.8, 0.8, 0.8, 1)
        )
        close_button.bind(on_press=self.dismiss)
        main_layout.add_widget(close_button)

        self.content = main_layout

        # Инициализация данных
        self.get_garrison()
        self.load_buildings()

        # Ссылки на виджеты гарнизона
        self.garrison_widgets = {}  # Словарь для хранения ссылок на виджеты гарнизона

    def load_buildings(self):
        """Загружает здания в интерфейс."""
        buildings = self.get_buildings()  # Получаем список зданий

        # Очищаем контейнер перед добавлением новых данных
        self.buildings_box.clear_widgets()

        # Если зданий нет, добавляем сообщение об этом
        if not buildings:
            label = Label(
                text="Зданий нет",
                size_hint_y=None,
                height=40,
                font_size='18sp',  # Увеличиваем размер шрифта
                color=(1, 0, 0, 1),  # Ярко-красный цвет текста
                halign='center',
                valign='middle'
            )
            label.bind(size=label.setter('text_size'))  # Для корректного выравнивания текста
            self.buildings_box.add_widget(label)
            return

        # Добавляем каждое здание в интерфейс
        for building in buildings:
            # Создаем макет для одного здания
            building_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

            # Информация о здании (текст с названием и количеством)
            text_container = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=5)
            with text_container.canvas.before:
                Color(0.1, 0.1, 0.1, 1)  # Темно-серый фон для контраста
                text_container.bg_rect = Rectangle(pos=text_container.pos, size=text_container.size)

            def update_rect(instance, value):
                """Обновляет позицию и размер фона при изменении размеров виджета."""
                if hasattr(instance, 'bg_rect'):
                    instance.bg_rect.pos = instance.pos
                    instance.bg_rect.size = instance.size

            text_container.bind(pos=update_rect, size=update_rect)

            # Текст с названием и количеством
            text_label = Label(
                text=building,
                font_size='18sp',  # Увеличиваем размер шрифта
                color=(1, 1, 1, 1),  # Белый цвет текста
                halign='left',
                valign='middle'
            )
            text_label.bind(size=text_label.setter('text_size'))  # Для корректного выравнивания текста
            text_container.add_widget(text_label)

            building_layout.add_widget(text_container)

            # Добавляем макет здания в контейнер
            self.buildings_box.add_widget(building_layout)

    def get_garrison(self):
        """Получает гарнизон города из таблицы garrisons"""
        try:
            # Запрос к базе данных для получения гарнизона
            self.cursor.execute("""
                SELECT unit_name, unit_count, unit_image 
                FROM garrisons 
                WHERE city_id = ?
            """, (self.city_name,))
            garrison_data = self.cursor.fetchall()

            # Очищаем контейнер с предыдущими данными
            self.attacking_units_box.clear_widgets()

            if not garrison_data:
                print(f"Гарнизон для города {self.city_name} пуст.")
                return

            print('Выполняется запрос к базе данных гарнизона', garrison_data)

            # Добавляем данные о каждом юните в интерфейс
            for unit_name, unit_count, unit_image in garrison_data:
                # Создаем макет для одного юнита
                unit_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=100, spacing=10)

                # Изображение юнита
                unit_image_widget = Image(
                    source=unit_image,
                    size_hint=(None, None),
                    size=(110, 110)  # Увеличиваем размер изображения
                )
                unit_layout.add_widget(unit_image_widget)

                # Информация о юните (текст с названием и количеством)
                text_container = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=5)
                with text_container.canvas.before:
                    Color(0.3, 0.3, 0.3, 1)
                    text_container.bg_rect = Rectangle(pos=text_container.pos, size=text_container.size)

                def update_rect(instance, value):
                    """Обновляет позицию и размер фона при изменении размеров виджета."""
                    if hasattr(instance, 'bg_rect'):
                        instance.bg_rect.pos = instance.pos
                        instance.bg_rect.size = instance.size

                text_container.bind(pos=update_rect, size=update_rect)

                # Текст с названием и количеством
                unit_text = f"{unit_name}\nКоличество: {format_number(unit_count)}"
                text_label = Label(
                    text=unit_text,
                    font_size='16sp',  # Увеличиваем размер шрифта
                    color=(1, 1, 1, 1),  # Белый текст
                    halign='left',
                    valign='middle'
                )
                text_label.bind(size=text_label.setter('text_size'))  # Для корректного выравнивания текста
                text_container.add_widget(text_label)

                unit_layout.add_widget(text_container)

                # Добавляем макет юнита в контейнер
                self.attacking_units_box.add_widget(unit_layout)

        except Exception as e:
            print(f"Ошибка при получении гарнизона: {e}")

    def get_buildings(self):
        """Получает количество зданий в указанном городе из таблицы buildings."""
        try:
            # Выполняем запрос к базе данных
            self.cursor.execute("""
                SELECT building_type, count 
                FROM buildings 
                WHERE city_name = ? AND faction = ?
            """, (self.city_name, self.ai_fraction))

            buildings_data = self.cursor.fetchall()

            # Формируем список с информацией о зданиях
            buildings = [f"{building_type}: {format_number(count)}" for building_type, count in buildings_data]

            # Если зданий нет, возвращаем пустой список
            return buildings if buildings else []

        except Exception as e:
            print(f"Ошибка при получении данных о зданиях: {e}")
            return []

    def select_troop_type(self, instance=None):
        """
        Открывает окно для выбора типа войск: Защитные, Атакующие, Любые.
        :param instance: Экземпляр виджета, который вызвал метод (не используется).
        """
        popup = Popup(title="Выберите тип войск", size_hint=(0.6, 0.4))
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Кнопки для выбора типа войск
        defensive_button = Button(text="Защитные", background_color=(0.6, 0.8, 0.6, 1))
        offensive_button = Button(text="Атакующие", background_color=(0.8, 0.6, 0.6, 1))
        any_button = Button(text="Любые", background_color=(0.6, 0.6, 0.8, 1))

        # Привязка действий к кнопкам
        defensive_button.bind(on_press=lambda btn: self.load_troops_by_type("Защитных", popup))
        offensive_button.bind(on_press=lambda btn: self.load_troops_by_type("Атакующих", popup))
        any_button.bind(on_press=lambda btn: self.load_troops_by_type("Любых", popup))

        # Добавляем кнопки в макет
        layout.add_widget(defensive_button)
        layout.add_widget(offensive_button)
        layout.add_widget(any_button)

        # Устанавливаем содержимое окна и открываем его
        popup.content = layout
        popup.open()

    def select_troops(self, selected_data):
        """
        Обрабатывает выбор войск для перемещения и выполняет обновление данных в базе данных.
        :param selected_data: Кортеж с данными о выбранном юните (город, название юнита, количество).
        """
        try:
            # Распаковываем данные о выбранном юните
            source_city_id, unit_name, unit_count = selected_data

            # Запрос у пользователя количества юнитов для переноса
            popup = Popup(title="Выберите количество", size_hint=(0.6, 0.4))
            layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

            input_label = Label(text=f"{unit_name} доступно:{format_number(unit_count)}")
            count_input = TextInput(multiline=False, input_filter='int')  # Разрешаем только целые числа
            layout.add_widget(input_label)
            layout.add_widget(count_input)

            # Добавляем метку для отображения ошибок
            error_label = Label(
                text="",
                color=(1, 0, 0, 1),  # Красный цвет текста
                size_hint_y=None,
                height=30
            )
            layout.add_widget(error_label)

            # Кнопки подтверждения и отмены
            button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
            confirm_button = Button(text="Подтвердить", background_color=(0.6, 0.8, 0.6, 1))
            cancel_button = Button(text="Отмена", background_color=(0.8, 0.6, 0.6, 1))

            def confirm_action(btn):
                try:
                    # Получаем введенное количество
                    taken_count = int(count_input.text)
                    if 0 < taken_count <= unit_count:
                        # Проверяем принадлежность города
                        destination_city_owner = self.get_city_owner(self.city_name)  # Владелец целевого города
                        current_player_kingdom = self.player_fraction  # Текущая фракция игрока

                        if destination_city_owner == current_player_kingdom:
                            # Свой город — разрешено перемещение
                            pass
                        elif self.is_ally(current_player_kingdom, destination_city_owner):
                            # Союзник — разрешено перемещение
                            pass
                        elif self.is_enemy(current_player_kingdom, destination_city_owner):
                            # Враг — разрешено нападение
                            pass
                        else:
                            # Нейтральный город — запрещено перемещение
                            error_label.text = "Нельзя перемещать войска в нейтральный город."
                            return

                        # Выполняем перенос войск
                        self.transfer_troops_between_cities(source_city_id, self.city_name, unit_name, taken_count)

                        # Закрываем окно ввода
                        popup.dismiss()

                        # Обновляем интерфейс гарнизона
                        self.update_garrison()

                        # Закрываем текущее окно выбора войск
                        self.close_current_popup()  # <--- ЗАКРЫВАЕМ ОКНО show_troops_selection

                    else:
                        # Показываем ошибку, если количество некорректно
                        error_label.text = "Ошибка: некорректное количество."

                except ValueError:
                    # Обработка случая, если ввод не является числом
                    error_label.text = "Ошибка: введите число."

            confirm_button.bind(on_press=confirm_action)
            cancel_button.bind(on_press=popup.dismiss)
            button_layout.add_widget(confirm_button)
            button_layout.add_widget(cancel_button)
            layout.add_widget(button_layout)

            popup.content = layout
            popup.open()

        except Exception as e:
            print(f"Ошибка при выборе войск: {e}")


    def load_troops_by_type(self, troop_type, previous_popup):
        """
        Загружает войска из гарнизонов в зависимости от выбранного типа.
        :param troop_type: Тип войск ("Defensive", "Offensive", "Any").
        :param previous_popup: Предыдущее всплывающее окно для закрытия.
        """
        try:
            # Закрываем предыдущее окно
            previous_popup.dismiss()

            # Шаг 1: Получаем все юниты из таблицы garrisons
            self.cursor.execute("""
                SELECT city_id, unit_name, unit_count, unit_image 
                FROM garrisons
            """)
            all_troops = self.cursor.fetchall()

            if not all_troops:
                # Если войск нет, показываем сообщение
                error_popup = Popup(
                    title="Ошибка",
                    content=Label(text=f"Нет доступных войск."),
                    size_hint=(0.6, 0.4)
                )
                error_popup.open()
                return

            # Шаг 2: Фильтруем юниты по типу (атакующие, защитные, любые) и фракции
            filtered_troops = []
            for city_id, unit_name, unit_count, unit_image in all_troops:
                # Получаем характеристики юнита из таблицы units
                self.cursor.execute("""
                    SELECT attack, defense, durability, faction 
                    FROM units 
                    WHERE unit_name = ?
                """, (unit_name,))
                unit_stats = self.cursor.fetchone()

                if not unit_stats:
                    print(f"Характеристики для юнита '{unit_name}' не найдены.")
                    continue

                attack, defense, durability, unit_faction = unit_stats

                # Проверяем принадлежность юнита к фракции игрока
                if unit_faction != self.player_fraction:
                    continue  # Пропускаем юниты других фракций

                # Определяем тип юнита
                if troop_type == "Защитных":
                    if defense > attack and defense > durability:
                        filtered_troops.append((city_id, unit_name, unit_count, unit_image))
                elif troop_type == "Атакующих":
                    if attack > defense and attack > durability:
                        filtered_troops.append((city_id, unit_name, unit_count, unit_image))
                else:  # "Any"
                    filtered_troops.append((city_id, unit_name, unit_count, unit_image))

            if not filtered_troops:
                # Если подходящих войск нет, показываем сообщение
                error_popup = Popup(
                    title="Ошибка",
                    content=Label(text=f"Нет доступных {troop_type.lower()} войск вашей фракции."),
                    size_hint=(0.6, 0.4)
                )
                error_popup.open()
                return

            # Открываем окно с выбором войск
            self.show_troops_selection(filtered_troops)

        except Exception as e:
            print(f"Ошибка при загрузке войск: {e}")

    def show_troops_selection(self, troops_data):
        """
        Отображает окно с выбором войск.
        :param troops_data: Список войск, полученный из базы данных.
        """
        popup = Popup(title="Выберите войска для перемещения", size_hint=(0.9, 0.9))
        self.current_popup = popup  # Сохраняем ссылку на текущее окно

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Создаем таблицу для отображения войск
        table_layout = GridLayout(cols=5, spacing=10, size_hint_y=None)
        table_layout.bind(minimum_height=table_layout.setter('height'))

        headers = ["Город", "Юнит", "Количество", "Изображение", "Действие"]
        for header in headers:
            label = Label(
                text=header,
                font_size='14sp',
                bold=True,
                size_hint_y=None,
                height=40,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(label)

        # Инициализация списка для хранения выбранных юнитов
        self.selected_group = []  # Группа для ввода войск
        self.selected_units_set = set()  # Множество для отслеживания добавленных юнитов

        # Словарь для хранения ссылок на виджеты строк таблицы
        self.table_widgets = {}

        for city_id, unit_name, unit_count, unit_image in troops_data:
            # Город
            city_label = Label(
                text=city_id,
                font_size='14sp',
                size_hint_y=None,
                height=60,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(city_label)

            # Юнит
            unit_label = Label(
                text=unit_name,
                font_size='14sp',
                size_hint_y=None,
                height=60,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(unit_label)

            # Количество
            count_label = Label(
                text=str(format_number(unit_count)),
                font_size='14sp',
                size_hint_y=None,
                height=60,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(count_label)

            # Изображение
            image_container = BoxLayout(size_hint_y=None, height=60)
            unit_image_widget = Image(
                source=unit_image,
                size_hint=(None, None),
                size=(50, 50)
            )
            image_container.add_widget(unit_image_widget)
            table_layout.add_widget(image_container)

            # Кнопка действия
            action_button = Button(
                text="Добавить",
                font_size='14sp',
                size_hint_y=None,
                height=40,
                background_color=(0.6, 0.8, 0.6, 1)
            )
            action_button.bind(on_press=lambda btn, data=(city_id, unit_name, unit_count, unit_image):
            self.create_troop_group(data, btn, city_label, unit_label, count_label, image_container, action_button))
            table_layout.add_widget(action_button)

            # Сохраняем ссылки на виджеты строки таблицы
            self.table_widgets[unit_name] = {
                "city_label": city_label,
                "unit_label": unit_label,
                "count_label": count_label,
                "image_container": image_container,
                "action_button": action_button
            }

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(table_layout)
        main_layout.add_widget(scroll_view)

        # Кнопка "Отправить группу в город"
        send_group_button = Button(
            text="Отправить группу в город",
            font_size='14sp',
            size_hint_y=None,
            height=50,
            background_color=(0.6, 0.8, 0.6, 1),
            disabled=True  # Кнопка изначально неактивна
        )
        send_group_button.bind(on_press=self.move_selected_group_to_city)
        self.send_group_button = send_group_button  # Сохраняем ссылку на кнопку

        # Кнопка для закрытия окна
        close_button = Button(text="Закрыть", size_hint_y=None, height=50, background_color=(0.8, 0.8, 0.8, 1))
        close_button.bind(on_press=popup.dismiss)

        # Добавляем кнопки в макет
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
        buttons_layout.add_widget(send_group_button)
        buttons_layout.add_widget(close_button)
        main_layout.add_widget(buttons_layout)

        popup.content = main_layout
        popup.open()

    def create_troop_group(self, troop_data, button, city_label, unit_label, count_label, image_container,
                           action_button):
        """
        Создает окно для добавления юнитов в группу с использованием слайдера для выбора количества.
        :param troop_data: Данные о юните (город, название, количество, изображение).
        :param button: Кнопка "Добавить", которую нужно обновить.
        :param city_label: Метка города.
        :param unit_label: Метка названия юнита.
        :param count_label: Метка количества юнитов.
        :param image_container: Контейнер изображения.
        :param action_button: Кнопка действия.
        """
        city_id, unit_name, unit_count, unit_image = troop_data

        # Создаем всплывающее окно
        popup = Popup(title=f"Добавление {unit_name} в группу", size_hint=(0.6, 0.5))
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Информация о юните
        info_label = Label(
            text=f"{unit_name}\nДоступно: {format_number(unit_count)}",
            font_size='14sp',
            size_hint_y=None,
            height=60,
            color=(1, 1, 1, 1)  # Черный текст
        )
        layout.add_widget(info_label)

        # Изображение юнита
        image_container = BoxLayout(size_hint_y=None, height=80)
        unit_image_widget = Image(
            source=unit_image,
            size_hint=(None, None),
            size=(70, 70)
        )
        image_container.add_widget(unit_image_widget)
        layout.add_widget(image_container)

        # Слайдер для выбора количества
        slider_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        slider_label = Label(
            text="Количество: 0",
            font_size='14sp',
            size_hint_x=None,
            width=100,
            color=(1, 1, 1, 1)
        )
        slider = Slider(min=0, max=unit_count, value=0, step=1)
        slider.bind(value=lambda instance, value: setattr(slider_label, 'text', f"Количество: {int(value)}"))
        slider_layout.add_widget(slider_label)
        slider_layout.add_widget(slider)
        layout.add_widget(slider_layout)

        # Метка для ошибок
        error_label = Label(
            text="",
            color=(1, 0, 0, 1),  # Красный цвет текста
            size_hint_y=None,
            height=30
        )
        layout.add_widget(error_label)

        # Кнопки подтверждения и отмены
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        confirm_button = Button(text="Подтвердить", background_color=(0.6, 0.8, 0.6, 1))
        cancel_button = Button(text="Отмена", background_color=(0.8, 0.6, 0.6, 1))

        def confirm_action(btn):
            try:
                selected_count = int(slider.value)
                if 0 < selected_count <= unit_count:
                    # Добавляем юнит в группу
                    self.selected_group.append({
                        "city_id": city_id,
                        "unit_name": unit_name,
                        "unit_count": selected_count,
                        "unit_image": unit_image
                    })
                    self.selected_units_set.add(unit_name)  # Отмечаем юнит как добавленный
                    popup.dismiss()  # Закрываем окно
                    print(f"Добавлено в группу: {unit_name} x {selected_count}")

                    # Активируем кнопку "Отправить группу в город", если группа не пуста
                    if self.selected_group and hasattr(self, "send_group_button") and self.send_group_button:
                        self.send_group_button.disabled = False

                    # Удаляем юнит из таблицы
                    unique_id = f"{city_id}_{unit_name}"
                    if unique_id in self.table_widgets:
                        widgets = self.table_widgets[unique_id]
                        table_layout = city_label.parent  # Получаем родительский контейнер

                        # Проверяем, что table_layout существует и виджеты находятся в нем
                        if table_layout and all(
                                widget in table_layout.children for widget in [
                                    widgets["city_label"],
                                    widgets["unit_label"],
                                    widgets["count_label"],
                                    widgets["image_container"],
                                    widgets["action_button"]
                                ]
                        ):
                            table_layout.remove_widget(widgets["city_label"])
                            table_layout.remove_widget(widgets["unit_label"])
                            table_layout.remove_widget(widgets["count_label"])
                            table_layout.remove_widget(widgets["image_container"])
                            table_layout.remove_widget(widgets["action_button"])
                            del self.table_widgets[unique_id]  # Удаляем запись из словаря
                        else:
                            print("Ошибка: Некоторые виджеты отсутствуют в table_layout.")
                else:
                    error_label.text = "Ошибка: некорректное количество."
            except ValueError:
                error_label.text = "Ошибка: введите корректное число."

        confirm_button.bind(on_press=confirm_action)
        cancel_button.bind(on_press=popup.dismiss)
        button_layout.add_widget(confirm_button)
        button_layout.add_widget(cancel_button)
        layout.add_widget(button_layout)

        popup.content = layout
        popup.open()

    def move_selected_group_to_city(self, instance=None):
        """
        Перемещает выбранную группу юнитов в город.
        :param instance: Экземпляр кнопки (не используется).
        """
        if not self.selected_group:
            show_popup_message("Ошибка", "Группа пуста. Добавьте юниты перед перемещением.")
            return

        try:
            for unit in self.selected_group:
                city_id = unit["city_id"]
                unit_name = unit["unit_name"]
                unit_count = unit["unit_count"]

                # Выполняем перенос юнитов
                self.transfer_troops_between_cities(
                    source_fortress_name=city_id,
                    destination_fortress_name=self.city_name,
                    unit_name=unit_name,
                    taken_count=unit_count
                )

            # Очищаем группу после перемещения
            self.selected_group.clear()
            self.update_garrison()  # Обновляем интерфейс гарнизона
        except Exception as e:
            show_popup_message("Ошибка", f"Произошла ошибка при перемещении группы: {e}")

    def update_garrison(self):
        """
        Обновляет данные о гарнизоне на интерфейсе с сохранением стиля.
        """
        try:
            # Очищаем текущие виджеты гарнизона
            self.attacking_units_box.clear_widgets()

            # Получаем актуальные данные о гарнизоне из базы данных
            cursor = self.cursor
            cursor.execute("""
                SELECT unit_name, unit_count, unit_image 
                FROM garrisons 
                WHERE city_id = ?
            """, (self.city_name,))
            garrison_data = cursor.fetchall()

            if not garrison_data:
                # Если гарнизон пуст, добавляем сообщение
                label = Label(
                    text="Гарнизон пуст",
                    size_hint_y=None,
                    height=60,
                    font_size='18sp',
                    color=(1, 0, 0, 1),  # Ярко-красный текст
                    halign='center',
                    valign='middle'
                )
                label.bind(size=label.setter('text_size'))  # Для корректного выравнивания текста
                self.attacking_units_box.add_widget(label)
                return

            # Добавляем новые виджеты для каждого юнита в гарнизоне
            for unit_name, unit_count, unit_image in garrison_data:
                # Создаем макет для одного юнита
                unit_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=100, spacing=10)

                # Изображение юнита
                unit_image_widget = Image(
                    source=unit_image,
                    size_hint=(None, None),
                    size=(110, 110)  # Увеличиваем размер изображения
                )
                unit_layout.add_widget(unit_image_widget)

                # Информация о юните (текст с названием и количеством)
                text_container = BoxLayout(orientation='vertical', size_hint=(1, 1), padding=5)
                with text_container.canvas.before:
                    Color(0.3, 0.3, 0.3, 1)  # Темно-серый фон
                    text_container.bg_rect = Rectangle(pos=text_container.pos, size=text_container.size)

                def update_rect(instance, value):
                    """Обновляет позицию и размер фона при изменении размеров виджета."""
                    if hasattr(instance, 'bg_rect'):
                        instance.bg_rect.pos = instance.pos
                        instance.bg_rect.size = instance.size

                text_container.bind(pos=update_rect, size=update_rect)

                # Текст с названием и количеством
                unit_text = f"{unit_name}\nКоличество: {format_number(unit_count)}"
                text_label = Label(
                    text=unit_text,
                    font_size='16sp',  # Увеличиваем размер шрифта
                    color=(1, 1, 1, 1),  # Белый текст
                    halign='left',
                    valign='middle'
                )
                text_label.bind(size=text_label.setter('text_size'))  # Для корректного выравнивания текста
                text_container.add_widget(text_label)

                unit_layout.add_widget(text_container)

                # Добавляем макет юнита в контейнер
                self.attacking_units_box.add_widget(unit_layout)

        except Exception as e:
            print(f"Ошибка при обновлении гарнизона: {e}")

    def show_warning_popup(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text="Для размещения юнитов сначала надо нанять!")
        btn = Button(text="OK", size_hint=(1, 0.3))

        popup = Popup(title="Внимание!", content=layout, size_hint=(0.5, 0.3))
        btn.bind(on_release=popup.dismiss)

        layout.add_widget(label)
        layout.add_widget(btn)

        popup.open()

    def place_army(self, instance):
        try:
            # Закрываем предыдущее всплывающее окно, если оно существует
            if self.current_popup:
                self.current_popup.dismiss()
                self.current_popup = None  # Очищаем ссылку

            cursor = self.cursor

            # Проверяем, принадлежит ли текущий город текущему игроку
            current_city_owner = self.get_city_owner(self.city_name)  # Получаем владельца текущего города
            current_player_kingdom = self.player_fraction  # Текущая фракция игрока

            if current_city_owner != current_player_kingdom:
                show_popup_message("Ошибка", "Вы не можете размещать войска в чужом городе.")
                return

            # Запрос для получения данных из таблицы armies
            cursor.execute("""
                SELECT unit_type, quantity, total_attack, total_defense, total_durability, unit_class, unit_image 
                FROM armies
            """)
            army_data = cursor.fetchall()

            if not army_data:
                print("Нет доступных юнитов для размещения.")
                self.show_warning_popup()
                return

            # Создаем новое всплывающее окно
            popup = Popup(title="Разместить армию", size_hint=(0.9, 0.9))
            self.current_popup = popup  # Сохраняем ссылку на текущее окно

            main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
            table_layout = GridLayout(cols=5, spacing=5, size_hint_y=None)  # Уменьшаем отступы между элементами
            table_layout.bind(minimum_height=table_layout.setter('height'))

            # Базовые параметры для масштабирования (еще меньше)
            base_font_size = 8  # Очень маленький базовый размер шрифта
            base_image_width, base_image_height = 50, 50  # Меньшие размеры изображений
            screen_width, _ = Window.size
            scale_factor = screen_width / 360  # Масштабный коэффициент

            font_size = int(base_font_size * scale_factor)
            image_width = int(base_image_width * scale_factor)
            image_height = int(base_image_height * scale_factor)

            headers = ["Изображение", "Название", "Количество", "Статистика", "Действие"]
            for header in headers:
                label = Label(
                    text=header,
                    font_size=f'{font_size}sp',
                    bold=True,
                    size_hint_y=None,
                    height=80,  # Уменьшаем высоту заголовков
                    color=(1, 1, 1, 1)
                )
                table_layout.add_widget(label)

            bg_color = (0.2, 0.2, 0.2, 1)  # Цвет окна интерфейса

            def update_rect(instance, value):
                if hasattr(instance, 'bg_rect'):
                    instance.bg_rect.pos = instance.pos
                    instance.bg_rect.size = instance.size

            # Список для отслеживания добавленных юнитов
            self.added_units = set()

            for unit in army_data:
                unit_type, quantity, attack, defense, durability, unit_class, unit_image = unit
                # Формируем данные о юните
                unit_data = {
                    "unit_type": unit_type,
                    "quantity": quantity,
                    "stats": {
                        "Атака": attack,
                        "Защита": defense,
                        "Живучесть": durability,
                        "Класс": unit_class
                    },
                    "unit_image": unit_image
                }

                # Изображение юнита
                image_container = BoxLayout(size_hint_y=None, height=image_height)
                unit_image_widget = KivyImage(
                    source=unit_image,
                    size_hint=(None, None),
                    size=(image_width, image_height)
                )
                image_container.add_widget(unit_image_widget)
                table_layout.add_widget(image_container)

                # Название юнита
                name_label = Label(
                    text=unit_type,
                    font_size=f'{font_size}sp',
                    size_hint_y=None,
                    height=70,  # Уменьшаем высоту
                    color=(1, 1, 1, 1)
                )
                with name_label.canvas.before:
                    Color(*bg_color)
                    name_label.bg_rect = Rectangle(pos=name_label.pos, size=name_label.size)
                name_label.bind(pos=update_rect, size=update_rect)
                table_layout.add_widget(name_label)

                # Количество юнитов
                count_label = Label(
                    text=str(format_number(quantity)),
                    font_size=f'{font_size}sp',
                    size_hint_y=None,
                    height=60,  # Уменьшаем высоту
                    color=(1, 1, 1, 1)
                )
                with count_label.canvas.before:
                    Color(*bg_color)
                    count_label.bg_rect = Rectangle(pos=count_label.pos, size=count_label.size)
                count_label.bind(pos=update_rect, size=update_rect)
                table_layout.add_widget(count_label)

                # Статистика юнита
                stats_text = "\n".join([
                    f"Атака: \n"
                    f"{format_number(attack)}",
                    f"Защита: \n"
                    f"{format_number(defense)}",
                    f"Живучесть: \n"
                    f"{format_number(durability)}",
                    f"Класс: {unit_class}"
                ])
                stats_label = Label(
                    text=stats_text,
                    font_size=f'{font_size}sp',
                    size_hint_y=None,
                    height=150,  # Уменьшаем высоту
                    color=(1, 1, 1, 1)
                )
                with stats_label.canvas.before:
                    Color(*bg_color)
                    stats_label.bg_rect = Rectangle(pos=stats_label.pos, size=stats_label.size)
                stats_label.bind(pos=update_rect, size=update_rect)
                table_layout.add_widget(stats_label)

                # Кнопка действия
                action_button = Button(
                    text="Добавить",
                    font_size=f'{font_size}sp',
                    size_hint_y=None,
                    height=70,  # Уменьшаем высоту кнопки
                    background_color=(0.6, 0.8, 0.6, 1)
                )
                action_button.bind(
                    on_press=lambda btn, data=unit_data, lbl=name_label: self.add_to_garrison_with_slider(data, lbl))
                table_layout.add_widget(action_button)

            scroll_view = ScrollView(size_hint=(1, 1))
            scroll_view.add_widget(table_layout)
            main_layout.add_widget(scroll_view)

            close_button = Button(
                text="Закрыть",
                font_size=f'{font_size}sp',
                size_hint_y=None,
                height=30,  # Уменьшаем высоту кнопки "Закрыть"
                background_color=(0.8, 0.8, 0.8, 1)
            )
            close_button.bind(on_press=popup.dismiss)
            main_layout.add_widget(close_button)

            popup.content = main_layout
            popup.open()

        except sqlite3.Error as e:
            show_popup_message("Ошибка", f"Произошла ошибка при работе с базой данных(place_army): {e}")
        except Exception as e:
            show_popup_message("Ошибка", f"Произошла ошибка: {e}")

    def add_to_garrison_with_slider(self, unit_data, name_label):
        """
        Открывает окно с ползунком для выбора количества войск и добавляет их в гарнизон.
        :param unit_data: Данные о юните.
        :param name_label: Метка с названием юнита для изменения цвета.
        """
        unit_type = unit_data["unit_type"]
        available_count = unit_data["quantity"]

        # Создаем всплывающее окно
        popup = Popup(title=f"Добавление {unit_type}", size_hint=(0.6, 0.4))
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Информация о юните
        info_label = Label(
            text=f"{unit_type}\nДоступно: {format_number(available_count)}",
            font_size='14sp',
            size_hint_y=None,
            height=60,
            color=(1, 1, 1, 1)
        )
        layout.add_widget(info_label)

        # Ползунок для выбора количества
        slider_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        slider_label = Label(
            text="Количество: 0",
            font_size='14sp',
            size_hint_x=None,
            width=100,
            color=(1, 1, 1, 1)
        )
        slider = Slider(min=0, max=available_count, value=0, step=1)
        slider.bind(value=lambda instance, value: setattr(slider_label, 'text', f"Количество: {int(value)}"))
        slider_layout.add_widget(slider_label)
        slider_layout.add_widget(slider)
        layout.add_widget(slider_layout)

        # Кнопки подтверждения и отмены
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        confirm_button = Button(text="Подтвердить", background_color=(0.6, 0.8, 0.6, 1))
        cancel_button = Button(text="Отмена", background_color=(0.8, 0.6, 0.6, 1))

        def confirm_action(btn):
            try:
                selected_count = int(slider.value)
                if 0 < selected_count <= available_count:
                    # Добавляем юнит в гарнизон
                    self.transfer_army_to_garrison(unit_data, selected_count)

                    # Закрываем текущее всплывающее окно
                    popup.dismiss()

                    # Обновляем интерфейс гарнизона
                    self.update_garrison()

                    # Изменяем цвет метки юнита на зеленый
                    name_label.color = (0, 1, 0, 1)  # Зеленый цвет
                    name_label.canvas.ask_update()  # Принудительно обновляем интерфейс
                else:
                    show_popup_message("Ошибка", "Некорректное количество.")
            except ValueError:
                show_popup_message("Ошибка", "Введите корректное число.")

        confirm_button.bind(on_press=confirm_action)
        cancel_button.bind(on_press=popup.dismiss)
        button_layout.add_widget(confirm_button)
        button_layout.add_widget(cancel_button)
        layout.add_widget(button_layout)

        popup.content = layout
        popup.open()

    def get_city_owner(self, fortress_name):
        try:
            cursor = self.cursor
            cursor.execute("""
                SELECT kingdom FROM city 
                WHERE fortress_name = ?
            """, (fortress_name,))
            result = cursor.fetchone()
            if not result:
                print(f"Город '{fortress_name}' не найден в таблице city.")
                return None
            print(f"Владелец города '{fortress_name}': {result[0]}")
            return result[0]
        except sqlite3.Error as e:
            print(f"Ошибка при получении владельца города: {e}")
            return None

    def initialize_turn_check_attack_faction(self):
        """
        Инициализирует запись в таблице turn_check_attack_faction, если её нет.
        Устанавливает значение check_attack в True по умолчанию.
        """
        try:
            cursor = self.cursor
            # Проверяем, существует ли уже запись для текущей фракции
            cursor.execute("""
                SELECT faction FROM turn_check_attack_faction 
                WHERE faction = ?
            """, (self.ai_fraction,))
            result = cursor.fetchone()

            if not result:
                # Если записи нет, создаем новую с check_attack = True
                cursor.execute("""
                    INSERT INTO turn_check_attack_faction (faction, check_attack)
                    VALUES (?, ?)
                """, (self.ai_fraction, True))
                self.conn.commit()
                print(f"Инициализирована запись для фракции {self.ai_fraction} с check_attack=True")
            else:
                print(f"Запись для фракции {self.ai_fraction} уже существует.")
        except sqlite3.Error as e:
            print(f"Ошибка при инициализации turn_check_attack_faction: {e}")

    def transfer_troops_between_cities(self, source_fortress_name, destination_fortress_name, unit_name, taken_count):
        """
        Переносит войска из одного города в другой с проверкой расстояния по координатам.
        :param source_fortress_name: Название исходного города/крепости.
        :param destination_fortress_name: Название целевого города/крепости.
        :param unit_name: Название юнита.
        :param taken_count: Количество юнитов для переноса.
        """
        try:
            cursor = self.cursor

            # Получаем владельцев городов
            source_owner = self.get_city_owner(source_fortress_name)
            destination_owner = self.get_city_owner(destination_fortress_name)

            if not source_owner or not destination_owner:
                show_popup_message("Ошибка", "Один из городов не существует.")
                return

            # Проверяем, что исходный город принадлежит текущему игроку
            current_player_kingdom = self.player_fraction

            # Получаем координаты городов
            source_coords = self.get_city_coordinates(source_fortress_name)
            destination_coords = self.get_city_coordinates(destination_fortress_name)

            # Вычисляем разницу между координатами
            x_diff = abs(source_coords[0] - destination_coords[0])
            y_diff = abs(source_coords[1] - destination_coords[1])
            total_diff = x_diff + y_diff
            print('total_diff:', total_diff)

            # Проверяем статус города назначения
            if destination_owner == current_player_kingdom:
                # Город назначения — свой
                self.move_troops(source_fortress_name, destination_fortress_name, unit_name, taken_count)
            elif self.is_ally(current_player_kingdom, destination_owner):
                # Город назначения — союзный
                if total_diff < 300:
                    self.move_troops(source_fortress_name, destination_fortress_name, unit_name, taken_count)
                else:
                    show_popup_message("Логистика не выдержит", "Слишком далеко. Найдите ближайший населенный пункт")
            elif self.is_enemy(current_player_kingdom, destination_owner):
                # Город назначения — вражеский
                if total_diff < 225:
                    # Проверяем флаг check_attack для фракции-цели
                    cursor.execute("""
                        SELECT check_attack FROM turn_check_attack_faction
                        WHERE faction = ?
                    """, (destination_owner,))
                    result = cursor.fetchone()

                    if result and result[0]:  # Если check_attack уже True
                        show_popup_message(
                            "Ошибка",
                            f"Фракция '{destination_owner}' уже была атакована на этом ходу."
                        )
                        return

                    # Устанавливаем check_attack в True для фракции-цели
                    cursor.execute("""
                        INSERT OR REPLACE INTO turn_check_attack_faction (faction, check_attack)
                        VALUES (?, ?)
                    """, (destination_owner, True))
                    self.conn.commit()

                    # Запускаем бой
                    self.start_battle_group(
                        source_fortress_name=source_fortress_name,
                        destination_fortress_name=destination_fortress_name,
                        attacking_units=self.selected_group
                    )
                else:
                    show_popup_message("Логистика не выдержит", "Слишком далеко. Найдите ближайший населенный пункт")
            else:
                # Город назначения — нейтральный, нельзя передавать войска
                show_popup_message("Ошибка", "Нельзя нападать на нейтральный город.")

        except sqlite3.Error as e:
            show_popup_message("Ошибка", f"Произошла ошибка при работе с базой данных(transfer): {e}")
        except Exception as e:
            show_popup_message("Ошибка", f"Произошла ошибка при переносе войск: {e}")

    def start_battle_group(self, source_fortress_name, destination_fortress_name, attacking_units):
        """
        Запускает сражение между атакующей и обороняющейся сторонами.
        :param source_fortress_name: Название исходного города/крепости.
        :param destination_fortress_name: Название целевого города/крепости.
        :param attacking_units: Список юнитов для атаки.
        """
        try:
            with self.conn:
                self.conn.row_factory = dict_factory
                cursor = self.conn.cursor()
                # Получаем владельцев городов
                source_owner = self.get_city_owner(source_fortress_name)
                destination_owner = self.get_city_owner(destination_fortress_name)
                # Проверяем наличие гарнизона в целевом городе
                cursor.execute("""
                    SELECT unit_name, unit_count, unit_image FROM garrisons WHERE city_id = ?
                """, (destination_fortress_name,))
                defending_garrison = cursor.fetchall()
                # Если гарнизон целевого города пуст, захватываем город без боя
                if not defending_garrison:
                    self.capture_city(destination_fortress_name, source_owner, attacking_units)
                    self.close_current_popup()  # Закрываем окно интерфейса
                    return
                # Собираем имена юнитов для оптимизации запросов
                unit_names = [
                    unit['unit_name'] for unit in attacking_units + defending_garrison
                    if isinstance(unit, dict) and 'unit_name' in unit
                ]
                placeholders = ', '.join(['?'] * len(unit_names))
                cursor.execute(f"""
                    SELECT unit_name, attack, durability, defense, unit_class, image_path 
                    FROM units 
                    WHERE unit_name IN ({placeholders})
                """, unit_names)
                unit_stats = {row['unit_name']: dict(row) for row in cursor.fetchall()}
                # Формируем списки армий
                attacking_army, defending_army = [], []
                for unit in attacking_units:
                    stats = unit_stats.get(unit['unit_name'])
                    if not stats:
                        print(f"Ошибка: данные о юните '{unit['unit_name']}' не найдены.")
                        continue
                    attacking_army.append({
                        "unit_name": unit['unit_name'],
                        "unit_count": unit['unit_count'],
                        "unit_image": stats.get("image_path", ""),
                        "units_stats": {
                            "Урон": stats["attack"],
                            "Живучесть": stats["durability"],
                            "Защита": stats["defense"],
                            "Класс юнита": stats["unit_class"]
                        }
                    })
                for unit in defending_garrison:
                    stats = unit_stats.get(unit['unit_name'])
                    if not stats:
                        print(f"Ошибка: данные о юните '{unit['unit_name']}' не найдены.")
                        continue
                    defending_army.append({
                        "unit_name": unit['unit_name'],
                        "unit_count": unit['unit_count'],
                        "unit_image": stats.get("image_path", ""),
                        "units_stats": {
                            "Урон": stats["attack"],
                            "Живучесть": stats["durability"],
                            "Защита": stats["defense"],
                            "Класс юнита": stats["unit_class"]
                        }
                    })
            # Запускаем бой (вне транзакции)
            fight(
                attacking_city=source_fortress_name,
                defending_city=destination_fortress_name,
                defending_army=defending_army,
                attacking_army=attacking_army,
                attacking_fraction=source_owner,
                defending_fraction=destination_owner,
                db_connection=self.conn
            )
            self.close_current_popup()
        except Exception as e:
            print(f"Ошибка при запуске боя: {e}")
            self.close_current_popup()

    def get_city_coordinates(self, city_name):
        """
        Возвращает координаты указанного города.
        :param city_name: Название города.
        :return: Кортеж (x, y) с координатами города.
        """
        cursor = self.cursor
        cursor.execute("SELECT coordinates FROM cities WHERE name = ?", (city_name,))
        result = cursor.fetchone()
        if result:
            # Преобразуем строку "[x, y]" в кортеж (x, y)
            coords_str = result[0].strip('[]')
            x, y = map(int, coords_str.split(','))
            return x, y
        raise ValueError(f"Город '{city_name}' не найден в базе данных.")

    def move_troops(self, source_fortress_name, destination_fortress_name, unit_name, taken_count):
        """
        Перемещает войска между городами.
        :param source_fortress_name: Название исходного города/крепости.
        :param destination_fortress_name: Название целевого города/крепости.
        :param unit_name: Название юнита.
        :param taken_count: Количество юнитов для переноса.
        """
        try:
            cursor = self.cursor

            # Шаг 1: Проверяем наличие юнитов в исходном городе
            cursor.execute("""
                SELECT unit_count, unit_image FROM garrisons 
                WHERE city_id = ? AND unit_name = ?
            """, (source_fortress_name, unit_name))
            source_unit = cursor.fetchone()

            if not source_unit or source_unit[0] < taken_count:
                print(f"Ошибка: недостаточно юнитов '{unit_name}' в городе '{source_fortress_name}'.")
                return

            # Получаем изображение юнита
            unit_image = source_unit[1]

            # Шаг 2: Обновляем количество юнитов в исходном городе
            remaining_count = source_unit[0] - taken_count
            if remaining_count > 0:
                cursor.execute("""
                    UPDATE garrisons 
                    SET unit_count = ? 
                    WHERE city_id = ? AND unit_name = ?
                """, (remaining_count, source_fortress_name, unit_name))
            else:
                cursor.execute("""
                    DELETE FROM garrisons 
                    WHERE city_id = ? AND unit_name = ?
                """, (source_fortress_name, unit_name))

            # Шаг 3: Проверяем наличие юнитов в целевом городе
            cursor.execute("""
                SELECT unit_count FROM garrisons 
                WHERE city_id = ? AND unit_name = ?
            """, (destination_fortress_name, unit_name))
            destination_unit = cursor.fetchone()

            if destination_unit:
                # Если юнит уже есть, увеличиваем его количество
                new_count = destination_unit[0] + taken_count
                cursor.execute("""
                    UPDATE garrisons 
                    SET unit_count = ? 
                    WHERE city_id = ? AND unit_name = ?
                """, (new_count, destination_fortress_name, unit_name))
            else:
                # Если юнита нет, добавляем новую запись с изображением
                cursor.execute("""
                    INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                    VALUES (?, ?, ?, ?)
                """, (destination_fortress_name, unit_name, taken_count, unit_image))

            # Сохраняем изменения в базе данных
            self.conn.commit()
            print("Войска успешно перенесены.")
            self.close_current_popup()

        except sqlite3.Error as e:
            print(f"Произошла ошибка при работе с базой данных(move_troops): {e}")
        except Exception as e:
            print(f"Произошла ошибка при переносе войск: {e}")

    def is_ally(self, faction1_id, faction2_id):
        """
        Проверяет, являются ли две фракции союзниками.
        :param faction1_id: Идентификатор первой фракции.
        :param faction2_id: Идентификатор второй фракции.
        :return: True, если фракции союзники, иначе False.
        """
        try:
            cursor = self.cursor
            cursor.execute("""
                SELECT relationship FROM diplomacies 
                WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
            """, (faction1_id, faction2_id, faction2_id, faction1_id))
            result = cursor.fetchone()
            return result and result[0] == "союз"
        except sqlite3.Error as e:
            print(f"Ошибка при проверке союзников: {e}")
            return False

    def is_enemy(self, faction1_id, faction2_id):
        """
        Проверяет, находятся ли две фракции в состоянии войны.
        :param faction1_id: Идентификатор первой фракции.
        :param faction2_id: Идентификатор второй фракции.
        :return: True, если фракции враги, иначе False.
        """
        try:
            cursor = self.cursor
            cursor.execute("""
                SELECT relationship FROM diplomacies 
                WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
            """, (faction1_id, faction2_id, faction2_id, faction1_id))
            result = cursor.fetchone()
            return result and result[0] == "война"
        except sqlite3.Error as e:
            print(f"Ошибка при проверке враждебности: {e}")
            return False

    def transfer_army_to_garrison(self, selected_unit, taken_count):
        """
        Переносит данные о войсках из таблицы armies в таблицу garrisons.
        :param selected_unit: Словарь с данными о юните (тип, статистика, изображение и т.д.).
        :param taken_count: Количество юнитов для переноса.
        """
        print('selected_unit прилетает в transfer_army_to_garrison в таком виде:', selected_unit)
        print(f'Количество юнитов для переноса: {taken_count}')
        try:
            cursor = self.cursor

            # Извлекаем данные из selected_unit
            unit_type = selected_unit.get("unit_type")
            stats = selected_unit.get("stats", {})
            unit_image = selected_unit.get("unit_image")

            # Проверяем, что все необходимые данные присутствуют
            if not all([unit_type, taken_count, stats, unit_image]):
                raise ValueError("Некорректные данные для переноса юнита.")

            # Преобразуем stats обратно в отдельные характеристики
            total_attack = stats.get("Attack", 0)
            total_defense = stats.get("Defense", 0)
            total_durability = stats.get("Durability", 0)

            # Получаем текущее количество юнитов из таблицы armies
            cursor.execute("""
                SELECT quantity, total_attack, total_defense, total_durability 
                FROM armies
                WHERE faction = ? AND unit_type = ?
            """, (self.player_fraction, unit_type))

            result = cursor.fetchone()

            if not result:
                print(f"Юнит '{unit_type}' не найден в таблице armies.")
                return

            old_count, current_attack, current_defense, current_durability = result

            # Проверяем, что можно взять указанное количество юнитов
            if taken_count > old_count:
                print(f"Ошибка: нельзя взять больше, чем есть. {unit_type}: {taken_count} > {old_count}")
                return

            # Проверяем, есть ли уже такой юнит в гарнизоне
            cursor.execute("""
                SELECT unit_count FROM garrisons 
                WHERE city_id = ? AND unit_name = ?
            """, (self.city_name, unit_type))

            existing_unit = cursor.fetchone()

            if existing_unit:
                # Если юнит уже есть, обновляем количество
                new_count = existing_unit[0] + taken_count
                cursor.execute("""
                    UPDATE garrisons 
                    SET unit_count = ? 
                    WHERE city_id = ? AND unit_name = ?
                """, (new_count, self.city_name, unit_type))
            else:
                # Если юнита нет, добавляем новую запись
                cursor.execute("""
                    INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                    VALUES (?, ?, ?, ?)
                """, (self.city_name, unit_type, taken_count, unit_image))

            # Обновляем оставшиеся войска в таблице armies
            remaining_count = old_count - taken_count
            if remaining_count > 0:
                cursor.execute("""
                    UPDATE armies 
                    SET quantity = ?, total_attack = ?, total_defense = ?, total_durability = ?
                    WHERE faction = ? AND unit_type = ?
                """, (
                    remaining_count,
                    round(current_attack * (remaining_count / old_count), 2),
                    round(current_defense * (remaining_count / old_count), 2),
                    round(current_durability * (remaining_count / old_count), 2),
                    self.player_fraction,
                    unit_type
                ))
            else:
                # Удаляем запись, если юнитов больше не осталось
                cursor.execute("""
                    DELETE FROM armies 
                    WHERE faction = ? AND unit_type = ?
                """, (self.player_fraction, unit_type))

            # Сохраняем изменения в базе данных
            self.conn.commit()
            print("Данные успешно перенесены из таблицы armies в таблицу garrisons.")
            self.close_current_popup()
        except sqlite3.Error as e:
            print(f"Произошла ошибка при работе с базой данных(transfer_army_to_garrison): {e}")
        except Exception as e:
            print(f"Произошла ошибка при переносе данных: {e}")

    def capture_city(self, fortress_name, new_owner, attacking_units):
        try:
            cursor = self.cursor

            # 1. Обновляем владельца города
            cursor.execute("""
                UPDATE city 
                SET kingdom = ? 
                WHERE fortress_name = ?
            """, (new_owner, fortress_name))

            cursor.execute("""
                UPDATE cities 
                SET faction = ? 
                WHERE name = ?
            """, (new_owner, fortress_name))

            # 2. Переносим только атакующие юниты
            for unit in attacking_units:
                # Удаляем из исходного города
                cursor.execute("""
                    UPDATE garrisons 
                    SET unit_count = unit_count - ? 
                    WHERE city_id = ? AND unit_name = ?
                """, (unit["unit_count"], unit["city_id"], unit["unit_name"]))

                # Удаляем запись, если юнитов больше нет
                cursor.execute("""
                    DELETE FROM garrisons 
                    WHERE city_id = ? AND unit_name = ? AND unit_count <= 0
                """, (unit["city_id"], unit["unit_name"]))

                # Добавляем в захваченный город
                cursor.execute("""
                    INSERT INTO garrisons 
                    (city_id, unit_name, unit_count, unit_image) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(city_id, unit_name) DO UPDATE 
                    SET unit_count = unit_count + ?
                """, (fortress_name, unit["unit_name"], unit["unit_count"],
                      unit["unit_image"], unit["unit_count"]))

            # 3. Передаем здания новому владельцу
            cursor.execute("""
                UPDATE buildings 
                SET faction = ? 
                WHERE city_name = ?
            """, (new_owner, fortress_name))

            self.conn.commit()
            show_popup_message("Успех", f"Город {fortress_name} захвачен!")
            self.update_garrison()

        except Exception as e:
            self.conn.rollback()
            show_popup_message("Ошибка", f"Ошибка захвата: {e}")


    def close_current_popup(self):
        """Закрывает текущее всплывающее окно."""
        if self.current_popup:
            self.current_popup.dismiss()
            self.current_popup = None  # Очищаем ссылку

    def close_popup(self):
        """
        Закрывает текущее всплывающее окно и освобождает ресурсы.
        """
        self.dismiss()  # Закрываем окно
        self.clear_widgets()  # Очищаем все виджеты


def show_popup_message(title, message):
    """
    Отображает всплывающее окно с сообщением поверх всех элементов.
    :param title: Заголовок окна.
    :param message: Текст сообщения.
    """
    # Создаем содержимое окна
    content = BoxLayout(orientation='vertical', padding=10, spacing=10)
    content.add_widget(Label(text=message, size_hint_y=None, height=50))

    # Кнопка закрытия окна
    close_button = Button(text="Закрыть", size_hint_y=None, height=50)
    content.add_widget(close_button)

    # Создаем всплывающее окно
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.7, 0.3),  # Размер окна (70% ширины и 30% высоты экрана)
        auto_dismiss=False  # Окно не закрывается автоматически при клике за его пределами
    )

    # Привязываем кнопку к закрытию окна
    close_button.bind(on_press=popup.dismiss)

    # Открываем окно
    popup.open()