from lerdon_libraries import *
from db_lerdon_connect import *

from fight import fight
from economic import format_number


class FortressInfoPopup(Popup):
    def __init__(self, ai_fraction, city_coords, player_fraction, conn, **kwargs):
        super(FortressInfoPopup, self).__init__(**kwargs)

        # Создаем подключение к БД
        self.conn = conn
        self.cursor = self.conn.cursor()
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
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
        Создает масштабируемый пользовательский интерфейс для окна города (Гарнизон / Здания).
        """
        from kivy.core.window import Window  # Убедимся, что Window доступен

        is_android = platform == 'android'

        # Базовые параметры для масштабирования
        screen_width, screen_height = Window.size
        scale_factor = screen_width / 360  # Относительно стандартной ширины

        base_font_size = 14 if is_android else 12
        base_button_height = dp(50) if is_android else 40
        padding = dp(15)
        spacing = dp(10)

        font_size = sp(base_font_size)
        button_height = base_button_height

        # Главный макет
        main_layout = BoxLayout(orientation='vertical', padding=padding, spacing=spacing)

        # === Верхняя часть: Гарнизон и здания в двух колонках ===
        columns_layout = GridLayout(cols=2, spacing=spacing, size_hint_y=0.7)

        # --- Левая колонка: Гарнизон ---
        troops_column = BoxLayout(orientation='vertical', spacing=spacing)

        troops_label = Label(
            text="Гарнизон",
            font_size=font_size * 1.2,
            bold=True,
            size_hint_y=None,
            height=dp(40),
            color=(1, 1, 1, 1)
        )
        troops_column.add_widget(troops_label)

        self.attacking_units_list = ScrollView(size_hint=(1, 1))
        self.attacking_units_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=spacing)
        self.attacking_units_box.bind(minimum_height=self.attacking_units_box.setter('height'))
        self.attacking_units_list.add_widget(self.attacking_units_box)
        troops_column.add_widget(self.attacking_units_list)
        columns_layout.add_widget(troops_column)

        # --- Правая колонка: Здания ---
        buildings_column = BoxLayout(orientation='vertical', spacing=spacing)

        buildings_label = Label(
            text="Здания",
            font_size=font_size * 1.2,
            bold=True,
            size_hint_y=None,
            height=dp(40),
            color=(1, 1, 1, 1)
        )
        buildings_column.add_widget(buildings_label)

        self.buildings_list = ScrollView(size_hint=(1, 1))
        self.buildings_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=spacing)
        self.buildings_box.bind(minimum_height=self.buildings_box.setter('height'))
        self.buildings_list.add_widget(self.buildings_box)
        buildings_column.add_widget(self.buildings_list)
        columns_layout.add_widget(buildings_column)

        main_layout.add_widget(columns_layout)

        # === Нижняя часть: Кнопки действий ===
        button_layout = BoxLayout(orientation='horizontal', spacing=spacing, size_hint_y=None, height=button_height)

        def create_styled_button(text, bg_color, height=dp(50) if is_android else 40):
            btn = Button(
                text=text,
                size_hint=(None, None),
                width=Window.width / 3 - spacing * 2,
                height=height,  # Теперь можно задать нужную высоту
                background_color=(0, 0, 0, 0),
                color=(1, 1, 1, 1),
                font_size=font_size,
            )
            with btn.canvas.before:
                Color(*bg_color)
                btn.rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[15])
            btn.bind(pos=lambda inst, val: setattr(inst.rect, 'pos', inst.pos))
            btn.bind(size=lambda inst, val: setattr(inst.rect, 'size', inst.size))
            return btn

        # Ввести войска
        send_troops_button = create_styled_button("Ввести войска", (0.2, 0.8, 0.2, 1),
                                                  height=dp(40) if is_android else 30)
        send_troops_button.size_hint_x = 1
        send_troops_button.bind(on_release=self.select_troop_type)
        button_layout.add_widget(send_troops_button)

        # Разместить армию
        place_army_button = create_styled_button("Разместить армию", (0.2, 0.6, 0.9, 1),
                                                 height=dp(40) if is_android else 30)
        place_army_button.size_hint_x = 1
        place_army_button.bind(on_release=self.place_army)
        button_layout.add_widget(place_army_button)

        main_layout.add_widget(button_layout)

        # === Кнопка "Закрыть" ===
        close_button = create_styled_button("Закрыть", (0.9, 0.3, 0.3, 1), height=dp(40) if is_android else 30)
        close_button.size_hint_x = 1
        close_button.bind(on_release=self.dismiss)
        main_layout.add_widget(close_button)

        self.content = main_layout

        # === Инициализация данных ===
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
                font_size='16sp',  # Увеличиваем размер шрифта
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
                    size=(120, 120)  # Увеличиваем размер изображения
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
                    font_size='17sp',  # Увеличиваем размер шрифта
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
        cursor = self.conn.cursor()
        try:
            # Выполняем запрос к базе данных
            cursor.execute("""
                SELECT building_type, count 
                FROM buildings 
                WHERE city_name = ? AND faction = ?
            """, (self.city_name, self.ai_fraction))

            buildings_data = cursor.fetchall()

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
        defensive_button.bind(on_release=lambda btn: self.load_troops_by_type("Защитных", popup))
        offensive_button.bind(on_release=lambda btn: self.load_troops_by_type("Атакующих", popup))
        any_button.bind(on_release=lambda btn: self.load_troops_by_type("Любых", popup))

        # Добавляем кнопки в макет
        layout.add_widget(defensive_button)
        layout.add_widget(offensive_button)
        layout.add_widget(any_button)

        # Устанавливаем содержимое окна и открываем его
        popup.content = layout
        popup.open()

    def load_troops_by_type(self, troop_type, previous_popup):
        """
        Загружает войска из гарнизонов в зависимости от выбранного типа.
        :param troop_type: Тип войск ("Defensive", "Offensive", "Any").
        :param previous_popup: Предыдущее всплывающее окно для закрытия.
        """
        try:
            # Закрываем предыдущее окно
            previous_popup.dismiss()
            cursor = self.conn.cursor()
            # Шаг 1: Получаем все юниты из таблицы garrisons
            cursor.execute("""
                SELECT city_id, unit_name, unit_count, unit_image 
                FROM garrisons
            """)
            all_troops = cursor.fetchall()

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
                cursor.execute("""
                    SELECT attack, defense, durability, faction 
                    FROM units 
                    WHERE unit_name = ?
                """, (unit_name,))
                unit_stats = cursor.fetchone()

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
                    content=Label(text=f"Нет доступных {troop_type} войск вашей фракции."),
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
                font_size='18sp',
                bold=True,
                size_hint_y=None,
                height=60,
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
                font_size='18sp',
                size_hint_y=None,
                height=90,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(city_label)

            # Юнит
            unit_label = Label(
                text=unit_name,
                font_size='18sp',
                size_hint_y=None,
                height=90,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(unit_label)

            # Количество
            count_label = Label(
                text=str(format_number(unit_count)),
                font_size='18sp',
                size_hint_y=None,
                height=90,
                color=(1, 1, 1, 1)  # Черный текст
            )
            table_layout.add_widget(count_label)

            # Изображение
            image_container = BoxLayout(size_hint_y=None, height=60)
            unit_image_widget = Image(
                source=unit_image,
                size_hint=(None, None),
                size=(80, 80)
            )
            image_container.add_widget(unit_image_widget)
            table_layout.add_widget(image_container)

            # Кнопка действия
            action_button = Button(
                text="Добавить",
                font_size='18sp',
                size_hint_y=None,
                height=80,
                background_color=(0.6, 0.8, 0.6, 1)
            )
            action_button.bind(on_release=lambda btn, data=(city_id, unit_name, unit_count, unit_image):
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
            font_size='17sp',
            size_hint_y=None,
            height=90,
            background_color=(0.6, 0.8, 0.6, 1),
            disabled=True  # Кнопка изначально неактивна
        )
        send_group_button.bind(on_release=self.move_selected_group_to_city)
        self.send_group_button = send_group_button  # Сохраняем ссылку на кнопку

        # Кнопка для закрытия окна
        close_button = Button(text="Закрыть", size_hint_y=None, height=80, background_color=(0.8, 0.8, 0.8, 1))
        close_button.bind(on_release=popup.dismiss)

        # Добавляем кнопки в макет
        buttons_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=90, spacing=10)
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
        popup = Popup(title=f"Добавление {unit_name} в группу", size_hint=(0.8, 0.7))
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Контейнер для изображения и количества
        top_section = BoxLayout(orientation='vertical', size_hint_y=None, height=120, spacing=10)

        # Метка количества
        selected_count_label = Label(
            text="Выбрано: 0",
            font_size='18sp',
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=30
        )

        # Добавляем изображение и метку количества в вертикальный контейнер
        top_section.add_widget(selected_count_label)
        layout.add_widget(top_section)

        # Слайдер для выбора количества
        slider_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=70, spacing=10)
        slider = Slider(min=0, max=unit_count, value=0, step=1)

        # Обновляем метки при изменении значения слайдера
        def update_labels(instance, value):
            selected_count_label.text = f"Выбрано: {int(value)}"

        slider.bind(value=update_labels)
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
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
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

                    # Активируем кнопку отправки группы
                    if self.selected_group and hasattr(self, "send_group_button") and self.send_group_button:
                        self.send_group_button.disabled = False

                    # Удаляем юнит из таблицы
                    unique_id = f"{city_id}_{unit_name}"
                    if unique_id in self.table_widgets:
                        widgets = self.table_widgets[unique_id]
                        table_layout = city_label.parent

                        if table_layout and all(widget in table_layout.children for widget in [
                            widgets["city_label"],
                            widgets["unit_label"],
                            widgets["count_label"],
                            widgets["image_container"],
                            widgets["action_button"]
                        ]):
                            table_layout.remove_widget(widgets["city_label"])
                            table_layout.remove_widget(widgets["unit_label"])
                            table_layout.remove_widget(widgets["count_label"])
                            table_layout.remove_widget(widgets["image_container"])
                            table_layout.remove_widget(widgets["action_button"])
                            del self.table_widgets[unique_id]
                        else:
                            print("Ошибка: Некоторые виджеты отсутствуют в table_layout.")
                else:
                    error_label.text = "Ошибка: некорректное количество."
            except ValueError:
                error_label.text = "Ошибка: введите корректное число."

        confirm_button.bind(on_release=confirm_action)
        cancel_button.bind(on_release=popup.dismiss)
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
            current_player_kingdom = self.player_fraction
            cursor = self.cursor

            # Проверка возможности перемещения (один раз на группу)
            cursor.execute("SELECT can_move FROM turn_check_move WHERE faction = ?", (current_player_kingdom,))
            move_data = cursor.fetchone()

            if not move_data:
                cursor.execute("""
                    INSERT INTO turn_check_move (faction, can_move)
                    VALUES (?, ?)
                """, (current_player_kingdom, True))
                self.conn.commit()
                move_data = (True,)
            elif not move_data[0]:
                show_popup_message("Ошибка", "Вы уже использовали своё перемещение на этом ходу.")
                return

            # === НОВАЯ ЛОГИКА: сначала проверяем возможность, потом выполняем ===
            from collections import defaultdict

            # Группируем юниты по исходным городам для проверки
            grouped_units = defaultdict(list)
            for unit in self.selected_group:
                grouped_units[unit["city_id"]].append(unit)

            # Проверяем каждую группу
            for source_city, units in grouped_units.items():
                for unit in units:
                    result = self.transfer_troops_between_cities(
                        source_fortress_name=source_city,
                        destination_fortress_name=self.city_name,
                        unit_name=unit["unit_name"],
                        taken_count=unit["unit_count"],
                        dry_run=True  # Только проверка, без изменений в БД
                    )
                    if not result:
                        # Если хотя бы одна проверка провалена — отменяем всё
                        return

            # Если все проверки пройдены — начинаем реальное выполнение
            for source_city, units in grouped_units.items():
                for unit in units:
                    self.transfer_troops_between_cities(
                        source_fortress_name=source_city,
                        destination_fortress_name=self.city_name,
                        unit_name=unit["unit_name"],
                        taken_count=unit["unit_count"],
                        dry_run=False
                    )

            # Теперь тратим право на перемещение
            cursor.execute("""
                UPDATE turn_check_move 
                SET can_move = ? 
                WHERE faction = ?
            """, (False, current_player_kingdom))
            self.conn.commit()

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
            cursor = self.conn.cursor()
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
            if self.current_popup:
                self.current_popup.dismiss()
                self.current_popup = None

            cursor = self.conn.cursor()
            current_city_owner = self.get_city_owner(self.city_name)
            current_player_kingdom = self.player_fraction

            if current_city_owner != current_player_kingdom:
                show_popup_message("Ошибка", "Вы не можете размещать войска в чужом городе.")
                return

            cursor.execute("""
                SELECT unit_type, quantity, total_attack, total_defense, total_durability, unit_class, unit_image 
                FROM armies
            """)
            army_data = cursor.fetchall()

            if not army_data:
                print("Нет доступных юнитов для размещения.")
                self.show_warning_popup()
                return

            # Создаем всплывающее окно
            popup = Popup(title="Разместить армию", size_hint=(0.95, 0.95))
            self.current_popup = popup

            screen_width, _ = Window.size
            scale_factor = screen_width / 360

            font_size = min(max(int(9 * scale_factor), 14), 18)
            image_size = int(80 * scale_factor)

            main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

            # ScrollView с карточками
            scroll_view = ScrollView(size_hint=(1, 1))
            card_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
            card_layout.bind(minimum_height=card_layout.setter('height'))

            # Цвет фона карточек
            card_bg_color = (0.15, 0.15, 0.15, 1)

            def create_card(unit):
                unit_type, quantity, attack, defense, durability, unit_class, unit_image = unit

                # Создаем unit_data в виде словаря, как в оригинальном коде
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

                card = BoxLayout(
                    orientation='horizontal',
                    spacing=10,
                    size_hint_y=None,
                    height=int(120 * scale_factor),
                    padding=10
                )

                # Изображение
                image = Image(
                    source=unit_image,
                    size_hint=(None, None),
                    size=(image_size, image_size)
                )

                # Информация
                info_layout = BoxLayout(orientation='vertical', spacing=5)
                name_label = Label(
                    text=unit_type,
                    font_size=sp(font_size + 2),
                    bold=True,
                    color=(1, 1, 1, 1),
                    size_hint_y=None,
                    height=int(30 * scale_factor)
                )

                stats_label = Label(
                    text=f"Атака: {str(format_number(attack))}\nЗащита: {str(format_number(defense))}\nЖивучесть: {str(format_number(durability))}\nКласс: {unit_class}",
                    font_size=sp(font_size - 1),
                    color=(0.9, 0.9, 0.9, 1),
                    size_hint_y=None,
                    height=int(60 * scale_factor),
                    valign='middle'
                )
                stats_label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))

                quantity_label = Label(
                    text=f"Доступно: {str(format_number(quantity))}",
                    font_size=sp(font_size - 1),
                    color=(0.7, 0.7, 0.7, 1)
                )

                info_layout.add_widget(name_label)
                info_layout.add_widget(stats_label)
                info_layout.add_widget(quantity_label)

                # Кнопка
                btn = Button(
                    text="Добавить",
                    font_size=sp(font_size),
                    size_hint=(None, None),
                    size=(int(50 * scale_factor), int(50 * scale_factor)),
                    background_color=(0.2, 0.6, 0.2, 1),
                    background_normal=''
                )
                btn.bind(on_release=lambda btn, data=unit_data: self.add_to_garrison_with_slider(data, btn))

                card.add_widget(image)
                card.add_widget(info_layout)
                card.add_widget(btn)

                # Фон карточки
                with card.canvas.before:
                    Color(*card_bg_color)
                    card.rect = Rectangle(pos=card.pos, size=card.size)
                card.bind(pos=lambda inst, val: setattr(inst.rect, 'pos', val))
                card.bind(size=lambda inst, val: setattr(inst.rect, 'size', val))

                return card

            # Добавляем карточки
            for unit in army_data:
                card_layout.add_widget(create_card(unit))

            scroll_view.add_widget(card_layout)
            main_layout.add_widget(scroll_view)

            # Кнопка закрытия
            close_btn = Button(
                text="Закрыть",
                font_size=sp(font_size + 1),
                size_hint=(1, None),
                height=int(30 * scale_factor),
                background_color=(0.2, 0.2, 0.2, 1),
                background_normal=''
            )
            close_btn.bind(on_release=popup.dismiss)
            main_layout.add_widget(close_btn)

            popup.content = main_layout
            popup.open()

        except sqlite3.Error as e:
            show_popup_message("Ошибка", f"Произошла ошибка при работе с базой данных (place_army): {e}")
        except Exception as e:
            show_popup_message("Ошибка", f"Произошла ошибка: {e}")

    def add_to_garrison_with_slider(self, unit_data, name_label):
        """
        Открывает адаптивное всплывающее окно с ползунком для выбора количества войск.
        """
        from kivy.metrics import dp, sp  # Убедитесь, что импортированы
        unit_type = unit_data["unit_type"]
        available_count = unit_data["quantity"]

        # Определение платформы
        is_mobile = platform == 'android' or platform == 'ios'

        # Расчёт ширины окна (95% ширины экрана без ограничения)
        window_width = Window.width * 0.95 if is_mobile else Window.width * 0.7
        # Высота окна с коррекцией для Android
        window_height = Window.height * 0.75 if is_mobile else Window.height * 0.4
        if is_mobile:
            window_height *= 0.9  # Компенсация высоты для Android

        # Создание Popup
        popup = Popup(
            title=f"",
            size_hint=(None, None),
            width=window_width,
            height=window_height,
            title_size=sp(20) if is_mobile else sp(18),
            background_color=(0.1, 0.1, 0.1, 0.95)
        )

        # Основной контейнер с адаптированными отступами
        layout = BoxLayout(
            orientation='vertical',
            padding=[dp(20), dp(15)],
            spacing=dp(20)
        )

        # === Ползунок с меткой ===
        slider_container = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(80) if is_mobile else dp(60),
            spacing=dp(15)
        )
        slider_label = Label(
            text="Количество: 0",
            font_size=sp(18) if is_mobile else sp(16),
            size_hint_x=0.4,
            color=(1, 1, 1, 1),
            halign='right',
            valign='middle'
        )
        slider_label.bind(size=slider_label.setter('text_size'))

        slider = Slider(
            min=0,
            max=available_count,
            value=0,
            step=1,
            size_hint_x=0.6,
            background_width=dp(40) if is_mobile else dp(30)
        )

        def update_slider_label(instance, value):
            slider_label.text = f"Количество: {int(value)}"

        slider.bind(value=update_slider_label)
        slider_container.add_widget(slider_label)
        slider_container.add_widget(slider)
        layout.add_widget(slider_container)

        # === Кнопки подтверждения ===
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(100) if is_mobile else dp(70),
            spacing=dp(25)
        )
        confirm_button = Button(
            text="Подтвердить",
            font_size=sp(20) if is_mobile else sp(16),
            background_color=(0.4, 0.7, 0.4, 1),
            background_normal='',
            border=[dp(15), dp(15), dp(15), dp(15)],
            size_hint_x=0.5
        )
        cancel_button = Button(
            text="Отмена",
            font_size=sp(20) if is_mobile else sp(16),
            background_color=(0.7, 0.4, 0.4, 1),
            background_normal='',
            border=[dp(15), dp(15), dp(15), dp(15)],
            size_hint_x=0.5
        )

        def confirm_action(btn):
            try:
                selected_count = int(slider.value)
                if 0 < selected_count <= available_count:
                    self.transfer_army_to_garrison(unit_data, selected_count)
                    popup.dismiss()
                    self.update_garrison()
                    name_label.color = (0, 1, 0, 1)
                else:
                    show_popup_message("Ошибка", f"Выберите количество от 1 до {available_count}")
            except ValueError:
                show_popup_message("Ошибка", "Введите корректное число")

        confirm_button.bind(on_release=confirm_action)
        cancel_button.bind(on_release=lambda btn: popup.dismiss())
        button_layout.add_widget(confirm_button)
        button_layout.add_widget(cancel_button)
        layout.add_widget(button_layout)

        # === Адаптация размера окна при изменении размера экрана ===
        def adapt_popup_size(*args):
            if is_mobile:
                popup.width = Window.width * 0.95
                popup.height = Window.height * 0.6 * 0.9
            else:
                popup.width = Window.width * 0.7
                popup.height = Window.height * 0.4

        Window.bind(on_resize=adapt_popup_size)
        popup.bind(on_dismiss=lambda _: Window.unbind(on_resize=adapt_popup_size))

        popup.content = layout
        popup.open()

    def get_city_owner(self, fortress_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT kingdom FROM city 
                WHERE fortress_name = ?
            """, (fortress_name,))
            result = cursor.fetchone()
            if not result:
                print(f"Город '{fortress_name}' не найден в таблице city.")
                return None

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
            cursor = self.conn.cursor()
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

    def initialize_turn_check_move(self):
        """
        Инициализирует запись о возможности перемещения для текущей фракции.
        Устанавливает значение 'can_move' = True по умолчанию.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turn_check_move (
                    faction TEXT PRIMARY KEY,
                    can_move BOOLEAN
                )
            """)
            self.conn.commit()

            # Проверяем, существует ли запись для текущей фракции
            cursor.execute("SELECT faction FROM turn_check_move WHERE faction = ?", (self.player_fraction,))
            result = cursor.fetchone()
            if not result:
                # Если записи нет, создаем новую с can_move = True
                cursor.execute("""
                    INSERT INTO turn_check_move (faction, can_move)
                    VALUES (?, ?)
                """, (self.player_fraction, True))
                self.conn.commit()
                print(f"Инициализирована запись для фракции {self.player_fraction} с can_move=True")
            else:
                print(f"Запись для фракции {self.player_fraction} уже существует.")
        except sqlite3.Error as e:
            print(f"Ошибка при инициализации turn_check_move: {e}")

    def transfer_troops_between_cities(self,
                                       source_fortress_name,
                                       destination_fortress_name,
                                       unit_name,
                                       taken_count,
                                       dry_run=False):
        """
        Переносит войска из одного города в другой с учётом обобщённых правил:
        1) Если войска в своём городе:
           — в свой город — без ограничений;
           — в союзный город — логистика < 300;
           — в вражеский город — логистика < 225 + проверка флага атаки;
           — в нейтральный город — запрещено.
        2) Если войска в городе союзника:
           — в любой город, принадлежащий текущему игроку или другим его союзникам — логистика < 300;
           — во все прочие (нейтральные/враждебные) — запрещено.
        3) Если войска в чужом (нейтральном или враждебном) городе — всегда запрещено.
        :param source_fortress_name: Название исходного города/крепости.
        :param destination_fortress_name: Название целевого города/крепости.
        :param unit_name: Название юнита.
        :param taken_count: Количество юнитов для переноса.
        :param dry_run: Если True — только проверяем возможность, не меняем данные.
        :return: True, если действие возможно, иначе False.
        """
        try:
            cursor = self.conn.cursor()
            # Получаем владельцев городов
            source_owner = self.get_city_owner(source_fortress_name)
            destination_owner = self.get_city_owner(destination_fortress_name)
            if not source_owner or not destination_owner:
                show_popup_message("Ошибка", "Один из городов не существует.")
                return False

            current_player_kingdom = self.player_fraction

            # Получаем координаты городов и считаем манхэттенское расстояние
            source_coords = self.get_city_coordinates(source_fortress_name)
            destination_coords = self.get_city_coordinates(destination_fortress_name)
            x_diff = abs(source_coords[0] - destination_coords[0])
            y_diff = abs(source_coords[1] - destination_coords[1])
            total_diff = x_diff + y_diff

            # ── 1) Сценарий: войска в своём городе ──────────────────────────────────────────
            if source_owner == current_player_kingdom:
                # — если цель свой город, разрешаем без ограничений;
                if destination_owner == current_player_kingdom:
                    if not dry_run:
                        self.move_troops(source_fortress_name,
                                         destination_fortress_name,
                                         unit_name,
                                         taken_count)
                    return True

                # — если цель союзник, проверяем total_diff < 300;
                elif self.is_ally(current_player_kingdom, destination_owner):
                    if total_diff < 300:
                        if not dry_run:
                            self.move_troops(source_fortress_name,
                                             destination_fortress_name,
                                             unit_name,
                                             taken_count)
                        return True
                    else:
                        show_popup_message("Логистика не выдержит",
                                           "Слишком далеко. Найдите ближайший населенный пункт")
                        return False

                # — если цель враг, проверяем total_diff < 225 и флаги атаки;
                elif self.is_enemy(current_player_kingdom, destination_owner):
                    if total_diff < 225:
                        cursor.execute(
                            "SELECT check_attack FROM turn_check_attack_faction WHERE faction = ?",
                            (destination_owner,)
                        )
                        attack_data = cursor.fetchone()
                        if attack_data and attack_data[0]:
                            show_popup_message("Ошибка",
                                               f"Фракция '{destination_owner}' уже была атакована на этом ходу.")
                            return False

                        if not dry_run:
                            # Отмечаем, что эту фракцию уже атаковали
                            cursor.execute(
                                "INSERT OR REPLACE INTO turn_check_attack_faction (faction, check_attack) VALUES (?, ?)",
                                (destination_owner, True)
                            )
                            self.conn.commit()

                            # Лишаем игрока права на дальнейшее перемещение в этом ходу
                            cursor.execute(
                                "UPDATE turn_check_move SET can_move = ? WHERE faction = ?",
                                (False, current_player_kingdom)
                            )
                            self.conn.commit()

                            # Запускаем бой
                            self.start_battle_group(source_fortress_name,
                                                    destination_fortress_name,
                                                    self.selected_group)
                        return True
                    else:
                        show_popup_message("Логистика не выдержит",
                                           "Слишком далеко. Найдите ближайший населенный пункт")
                        return False

                # — иначе (нейтральный), запрещаем.
                else:
                    show_popup_message("Ошибка", "Нельзя нападать на нейтральный город.")
                    return False

            # ── 2) Сценарий: войска в городе союзника ────────────────────────────────────
            elif self.is_ally(current_player_kingdom, source_owner):
                # Разрешаем перемещать войска из города союзника:
                # — либо в любой город текущего игрока,
                # — либо в город любого другого союзника.
                # Лимит логистики тот же, что и для переходов «свой→союзник» (300).

                # Проверяем, является ли назначение своим городом или городом другого союзника
                if (destination_owner == current_player_kingdom or
                        self.is_ally(current_player_kingdom, destination_owner)):
                    if total_diff < 300:
                        if not dry_run:
                            self.move_troops(source_fortress_name,
                                             destination_fortress_name,
                                             unit_name,
                                             taken_count)
                        return True
                    else:
                        show_popup_message("Логистика не выдержит",
                                           "Слишком далеко. Найдите ближайший населенный пункт")
                        return False
                else:
                    # Попытка отправить войска из города союзника в нейтральный или враждебный город
                    show_popup_message("Ошибка",
                                       "Вы можете перемещать войска из города союзника только в свои города или в города союзника.")
                    return False

            # ── 3) Во всех остальных случаях (нейтральный или враждебный источник) ───────
            else:
                show_popup_message("Ошибка",
                                   "Вы можете перемещать свои войска на свою территорию только из города союзника.")
                return False

        except sqlite3.Error as e:
            show_popup_message("Ошибка",
                               f"Произошла ошибка при работе с базой данных (transfer): {e}")
            return False
        except Exception as e:
            show_popup_message("Ошибка",
                               f"Произошла ошибка при переносе войск: {e}")
            return False

    def start_battle_group(self, source_fortress_name, destination_fortress_name, attacking_units):
        try:
            with self.conn:
                try:
                    self.conn.execute("PRAGMA wal_checkpoint(FULL);")
                except sqlite3.Error as e:
                    print(f"[WARNING] Не удалось выполнить wal_checkpoint: {e}")

                cursor = self.conn.cursor()

                source_owner = self.get_city_owner(source_fortress_name)
                destination_owner = self.get_city_owner(destination_fortress_name)

                if not source_owner or not destination_owner:
                    print(f"[ERROR] Не удалось определить фракции. source={source_owner}, dest={destination_owner}")
                    show_popup_message("Ошибка", "Не удалось определить фракции.")
                    return

                # вытаскиваем гарнизон
                cursor.execute(
                    "SELECT unit_name, unit_count, unit_image FROM garrisons WHERE city_id = ?",
                    (destination_fortress_name,)
                )
                rows = cursor.fetchall()
                # вот здесь конвертим Row в dict
                defending_garrison = [dict(row) for row in rows]
                print(f"defending_garrison={defending_garrison}")

                if not defending_garrison:
                    self.capture_city(destination_fortress_name, source_owner, attacking_units)
                    self.close_current_popup()
                    return

                # собираем имена из атакующих
                unit_names = {u.get('unit_name', '').strip() for u in attacking_units if u.get('unit_name')}
                # и из защищающихся
                for unit in defending_garrison:
                    name = unit.get('unit_name', '').strip()
                    if name:
                        unit_names.add(name)
                unit_names = list(unit_names)
                print(f"unit_names={unit_names}")

                if not unit_names:
                    print("[WARNING] Нет имён юнитов для запроса характеристик.")
                    show_popup_message("Ошибка", "Нет данных о юнитах для боя.")
                    return

                # достаём статы
                placeholders = ','.join('?' * len(unit_names))
                query = f"""
                    SELECT unit_name, attack, durability, defense, unit_class, image_path 
                    FROM units 
                    WHERE unit_name IN ({placeholders})
                """
                cursor.execute(query, unit_names)
                results = cursor.fetchall()

                cols = [d[0] for d in cursor.description]
                idx = {k: cols.index(k) for k in
                       ('unit_name', 'attack', 'durability', 'defense', 'unit_class', 'image_path')}

                unit_stats = {
                    row[idx['unit_name']].strip(): {
                        'unit_name': row[idx['unit_name']].strip(),
                        'attack': row[idx['attack']],
                        'durability': row[idx['durability']],
                        'defense': row[idx['defense']],
                        'unit_class': row[idx['unit_class']],
                        'image_path': row[idx['image_path']],
                    }
                    for row in results
                }

                # Формируем армии
                attacking_army = []
                for u in attacking_units:
                    name = u.get('unit_name', '').strip()
                    stats = unit_stats.get(name)
                    if not stats:
                        print(f"Ошибка: данные о юните '{name}' не найдены.")
                        continue
                    attacking_army.append({
                        "unit_name": name,
                        "unit_count": u.get('unit_count', 0),
                        "unit_image": stats['image_path'],
                        "units_stats": {
                            "Урон": stats['attack'],
                            "Живучесть": stats['durability'],
                            "Защита": stats['defense'],
                            "Класс юнита": stats['unit_class'],
                        }
                    })

                defending_army = []
                for u in defending_garrison:
                    name = u.get('unit_name', '').strip()
                    stats = unit_stats.get(name)
                    if not stats:
                        print(f"Ошибка: данные о юните '{name}' не найдены.")
                        continue
                    defending_army.append({
                        "unit_name": name,
                        "unit_count": u.get('unit_count', 0),
                        "unit_image": stats['image_path'],
                        "units_stats": {
                            "Урон": stats['attack'],
                            "Живучесть": stats['durability'],
                            "Защита": stats['defense'],
                            "Класс юнита": stats['unit_class'],
                        }
                    })

                # Запускаем сам бой
                fight(
                    attacking_city=source_fortress_name,
                    defending_city=destination_fortress_name,
                    defending_army=defending_army,
                    attacking_army=attacking_army,
                    attacking_fraction=source_owner,
                    defending_fraction=destination_owner,
                    conn=self.conn
                )
                self.close_current_popup()

        except sqlite3.Error as e:
            print(f"[ERROR] Ошибка базы данных при запуске боя: {e}")
            show_popup_message("Ошибка", f"Ошибка БД: {e}")
            self.close_current_popup()
        except Exception as e:
            print(f"[ERROR] Неожиданная ошибка при запуске боя: {e}")
            show_popup_message("Ошибка", f"Неизвестная ошибка: {e}")
            self.close_current_popup()

    def capture_city(self, fortress_name, new_owner, attacking_units):
        try:
            with self.conn:
                cursor = self.conn.cursor()

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

            show_popup_message("Успех", f"Город {fortress_name} захвачен!")
            self.update_garrison()

        except sqlite3.Error as e:
            show_popup_message("Ошибка", f"Ошибка при захвате города: {e}")

    def get_city_coordinates(self, city_name):
        """
        Возвращает координаты указанного города.
        :param city_name: Название города.
        :return: Кортеж (x, y) с координатами города.
        """
        cursor = self.conn.cursor()
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
            cursor = self.conn.cursor()

            # Шаг 1: Проверяем наличие юнитов в исходном городе
            cursor.execute("""
                SELECT unit_count, unit_image FROM garrisons 
                WHERE city_id = ? AND unit_name = ?
            """, (source_fortress_name, unit_name))
            source_unit = cursor.fetchone()

            if not source_unit or source_unit[0] < taken_count:
                print(f"Ошибка: недостаточно юнитов '{unit_name}' в городе '{source_fortress_name}'.")
                return

            unit_image = source_unit[1]
            remaining_count = source_unit[0] - taken_count

            # Шаг 2: Обновляем количество юнитов в исходном городе
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
                new_count = destination_unit[0] + taken_count
                cursor.execute("""
                    UPDATE garrisons 
                    SET unit_count = ? 
                    WHERE city_id = ? AND unit_name = ?
                """, (new_count, destination_fortress_name, unit_name))
            else:
                cursor.execute("""
                    INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                    VALUES (?, ?, ?, ?)
                """, (destination_fortress_name, unit_name, taken_count, unit_image))

            self.conn.commit()  # Фиксируем изменения
            print("Войска успешно перенесены.")
            self.close_current_popup()

        except sqlite3.Error as e:
            self.conn.rollback()  # Откатываем изменения
            print(f"[ERROR] Ошибка SQLite при перемещении войск: {e}")
            show_popup_message("Ошибка", f"Не удалось переместить войска: {e}")

        except Exception as e:
            self.conn.rollback()
            print(f"[ERROR] Неожиданная ошибка при перемещении войск: {e}")
            show_popup_message("Ошибка", f"Произошла системная ошибка: {e}")

    def is_ally(self, faction1_id, faction2_id):
        """
        Проверяет, являются ли две фракции союзниками.
        :param faction1_id: Идентификатор первой фракции.
        :param faction2_id: Идентификатор второй фракции.
        :return: True, если фракции союзники, иначе False.
        """
        try:
            cursor = self.conn.cursor()
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
            cursor = self.conn.cursor()
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
        try:
            with self.conn:
                cursor = self.conn.cursor()

                unit_type = selected_unit.get("unit_type")
                stats = selected_unit.get("stats", {})
                unit_image = selected_unit.get("unit_image")

                if not all([unit_type, taken_count, stats, unit_image]):
                    raise ValueError("Некорректные данные для переноса юнита.")

                # Получаем текущее количество юнитов в гарнизоне
                cursor.execute("""
                    SELECT unit_count FROM garrisons 
                    WHERE city_id = ? AND unit_name = ?
                """, (self.city_name, unit_type))
                existing_unit = cursor.fetchone()

                if existing_unit:
                    new_count = existing_unit[0] + taken_count
                    cursor.execute("""
                        UPDATE garrisons 
                        SET unit_count = ? 
                        WHERE city_id = ? AND unit_name = ?
                    """, (new_count, self.city_name, unit_type))
                else:
                    cursor.execute("""
                        INSERT INTO garrisons 
                        (city_id, unit_name, unit_count, unit_image) 
                        VALUES (?, ?, ?, ?)
                    """, (self.city_name, unit_type, taken_count, unit_image))

                # Уменьшаем количество юнитов в армии
                cursor.execute("""
                    UPDATE armies 
                    SET quantity = quantity - ? 
                    WHERE unit_type = ?
                """, (taken_count, unit_type))

                cursor.execute("""
                    DELETE FROM armies 
                    WHERE unit_type = ? AND quantity <= 0
                """, (unit_type,))

            self.update_garrison()
            self.close_current_popup()

        except sqlite3.Error as e:
            show_popup_message("Ошибка", f"Не удалось перенести юниты: {e}")
        except Exception as e:
            show_popup_message("Ошибка", f"Произошла ошибка: {e}")

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
    Отображает всплывающее окно с сообщением,
    расположенным по центру, белым цветом и размером 18sp.
    :param title: Заголовок окна.
    :param message: Текст сообщения (короткий, без прокрутки).
    """

    # Основной контейнер: заполняет всё пространство popup
    content = BoxLayout(
        orientation='vertical',
        padding=dp(15),
        spacing=dp(10),
        size_hint=(1, 1)
    )

    # Label с сообщением: белый цвет, 18sp, по центру и внутри
    message_label = Label(
        text=message,
        size_hint=(1, 1),
        font_size=dp(18),
        color=(1, 1, 1, 1),  # чисто белый
        halign='center',
        valign='middle'
    )
    # Чтобы текст правильно оборачивался и центрировался внутри Label:
    # связываем text_size с размером самой метки
    message_label.bind(size=lambda instance, value: instance.setter('text_size')(instance, value))

    content.add_widget(message_label)

    # Кнопка «Закрыть» внизу
    close_button = Button(
        text="Закрыть",
        size_hint_y=None,
        height=dp(50),
        background_color=get_color_from_hex("#4CAF50"),
        background_normal='',
        color=(1, 1, 1, 1),
        font_size=dp(16),
        bold=True
    )
    content.add_widget(close_button)

    # Размер popup: максимум 90% ширины и 70% высоты экрана
    popup_width = min(dp(500), Window.width * 0.9)
    popup_height = min(dp(600), Window.height * 0.7)

    # Создаём само окно. Фон сделаем тёмным, чтобы белый текст был хорошо виден.
    popup = Popup(
        title=title,
        title_size=dp(18),
        title_align='center',
        title_color=get_color_from_hex("#FFFFFF"),
        content=content,
        separator_color=get_color_from_hex("#FFFFFF"),
        separator_height=dp(1),
        size_hint=(None, None),
        size=(popup_width, popup_height),
        background_color=(0.15, 0.15, 0.15, 1),  # тёмно-серый фон (чтобы белый текст читался)
        overlay_color=(0, 0, 0, 0.5),
        auto_dismiss=False
    )

    # Обработчик изменения размера окна (если пользователь повернёт экран или сменит размер)
    def update_size(*args):
        new_w = min(dp(500), Window.width * 0.9)
        new_h = min(dp(600), Window.height * 0.7)
        popup.size = (new_w, new_h)

    Window.bind(on_resize=update_size)
    popup.bind(on_dismiss=lambda *x: Window.unbind(on_resize=update_size))

    close_button.bind(on_release=popup.dismiss)

    popup.open()
