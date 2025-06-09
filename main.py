
from lerdon_libraries import *
from game_process import GameScreen
from ui import *
from db_lerdon_connect import *

class AuthorScreen(Screen):
    def __init__(self, **kwargs):
        super(AuthorScreen, self).__init__(**kwargs)

        root = FloatLayout()

        # Фоновое видео
        video = Video(source="files/menu/author.mp4",
                      options={'eos': 'loop'},
                      state='play',
                      allow_stretch=True,
                      keep_ratio=False,
                      volume=0)
        video.size_hint = (1, 1)
        video.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        root.add_widget(video)

        # Прозрачный слой с контентом
        layout = BoxLayout(orientation='vertical',
                           padding=dp(20),
                           spacing=dp(20),
                           size_hint=(0.9, 0.8),
                           pos_hint={'center_x': 0.5, 'center_y': 0.5})

        # Заголовок
        title_label = Label(
            text="[b]Сообщество Лэрдона[/b]",
            markup=True,
            font_size='28sp',
            size_hint_y=None,
            height=dp(50),
            color=(1, 1, 1, 1),
            halign="center"
        )
        layout.add_widget(title_label)

        # Ссылки-карточки
        link_box = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(100))

        vk_label = Label(
            text="[ref=https://vk.com/destianfarbius][color=#00aaff]Страница автора ВКонтакте[/color][/ref]",
            markup=True,
            font_size='18sp',
            size_hint_y=None,
            height=dp(40),
            halign="center",
            valign="middle"
        )
        vk_label.bind(on_ref_press=self.open_link)

        tg_label = Label(
            text="[ref=https://t.me/+scOGK6ph6r03YmU6][color=#00aaff]Присоединиться к Telegram[/color][/ref]",
            markup=True,
            font_size='18sp',
            size_hint_y=None,
            height=dp(40),
            halign="center",
            valign="middle"
        )
        tg_label.bind(on_ref_press=self.open_link)

        link_box.add_widget(vk_label)
        link_box.add_widget(tg_label)
        layout.add_widget(link_box)

        # Кнопка "Назад" — уменьшена
        back_button = Button(
            text="Назад",
            size_hint=(0.3, None),
            height=dp(40),
            pos_hint={'center_x': 0.5},
            background_color=(0.2, 0.6, 1, 0.8),
            color=(1, 1, 1, 1),
            font_size='14sp'
        )
        back_button.bind(on_press=self.go_back)
        layout.add_widget(back_button)

        root.add_widget(layout)
        self.add_widget(root)

    def go_back(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(MenuWidget())

    def open_link(self, instance, url):
        webbrowser.open(url)


class LoadingScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(LoadingScreen, self).__init__(**kwargs)

        # === Фон через Canvas ===
        with self.canvas.before:
            self.bg_rect = Rectangle(
                source='files/menu/loading_bg.jpg',
                pos=self.pos,
                size=self.size
            )
        self.bind(pos=self._update_bg, size=self._update_bg)

        # === Прогресс-бар ===
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint=(1, None),
            height=dp(30),
            pos_hint={'center_x': 0.5, 'center_y': 0.2}
        )

        # Обёртка для стилизации прогресс-бара
        self.pb_container = FloatLayout(
            size_hint=(0.8, None),
            height=dp(30)
        )
        self.pb_container.pos_hint = {'center_x': 0.5, 'center_y': 0.2}

        with self.pb_container.canvas.before:
            # Тёмный фон контейнера прогресс-бара
            Color(0.2, 0.2, 0.2, 1)
            self.pb_rect = Rectangle(size=self.pb_container.size, pos=self.pb_container.pos)

            # Заливка (синяя) прогресса
            Color(0, 0.7, 1, 1)
            self.pb_fill = Rectangle(size=(0, self.pb_container.height), pos=self.pb_container.pos)

        self.pb_container.bind(pos=self.update_pb_canvas, size=self.update_pb_canvas)
        self.pb_container.add_widget(self.progress_bar)
        self.add_widget(self.pb_container)

        # === Подпись с процентами ===
        self.label = Label(
            markup=True,
            text="",
            font_size='19sp',
            pos_hint={'center_x': 0.5, 'center_y': 0.11},
            size_hint=(1, None),
            halign='center'
        )
        self.add_widget(self.label)

        # Запускаем последовательность загрузки
        Clock.schedule_once(self.start_loading)

    def update_pb_canvas(self, *args):
        # Обновляем фон контейнера прогресс-бара
        self.pb_rect.pos = self.pb_container.pos
        self.pb_rect.size = self.pb_container.size

        # Обновляем саму заливку в зависимости от value
        fill_width = self.progress_bar.value / 100 * self.pb_container.width
        self.pb_fill.pos = self.pb_container.pos
        self.pb_fill.size = (fill_width, self.pb_container.height)

    # === Методы загрузки ===
    def start_loading(self, dt):
        self.current_progress = 0
        self.loading_steps = [
            self.step_check_db,
            self.step_cleanup_cache,
            self.step_restore_backup,
            self.step_load_assets,
            self.step_complete
        ]
        self.run_next_step()

    def run_next_step(self, *args):
        if self.loading_steps:
            step = self.loading_steps.pop(0)
            step()
        else:
            # Дошли до 100%
            self.progress_bar.value = 100
            self.update_pb_canvas()
            self.label.text = "[color=#00ff00]В БОЙ![/color]"
            Clock.schedule_once(self.switch_to_menu, 0.8)

    def update_progress(self, delta):
        self.current_progress += delta
        self.progress_bar.value = self.current_progress
        percent = int(self.current_progress)
        self.label.text = f"[color=#00ccff]Готовим ресурсы... {percent}%[/color]"
        self.update_pb_canvas()

    # === Шаги загрузки ===
    def step_check_db(self):
        print("Шаг 1: Проверка базы данных...")
        self.update_progress(20)
        Clock.schedule_once(self.run_next_step, 0.3)

    def step_cleanup_cache(self):
        print("Шаг 2: Очистка кэша...")
        self.update_progress(20)
        Clock.schedule_once(self.run_next_step, 0)

    def step_restore_backup(self):
        print("Шаг 3: Восстановление из бэкапа...")
        self.update_progress(20)
        Clock.schedule_once(self.run_next_step, 0)

    def step_load_assets(self):
        print("Шаг 4: Подготовка ресурсов...")
        time.sleep(0.5)
        self.update_progress(20)
        Clock.schedule_once(self.run_next_step, 0)

    def step_complete(self):
        print("Шаг 5: Подготовка перехода в меню...")
        self.update_progress(20)
        Clock.schedule_once(self.run_next_step, 0)

    def _update_bg(self, *args):
        # Делаем так, чтобы фон всегда тянулся на весь экран
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def switch_to_menu(self, dt):
        # --- Сначала меняем фон ---
        self.bg_rect.source = 'files/menu/main_fon.jpg'
        self.bg_rect.texture = CoreImage('files/menu/main_fon.jpg').texture

        # --- Убираем все дочерние виджеты (прогресс-бар, подпись и т.д.) ---
        self.clear_widgets()
        self.add_widget(MenuWidget())


RANK_TO_FILENAME = {
    "Главнокомандующий":        "supreme_commander.png",
    "Верховный маршал":          "supreme_marshal.png",
    "Генерал-фельдмаршал":       "field_marshal.png",
    "Генерал армии":             "general.png",
    "Генерал-полковник":         "colonel_general.png",
    "Генерал-лейтенант":         "lieutenant_general.png",
    "Генерал-майор":             "major_general.png",
    "Бригадный генерал":         "brigadier_general.png",
    "Коммандер":                 "commander.png",
    "Полковник":                 "colonel.png",
    "Подполковник":              "lieutenant_colonel.png",
    "Майор":                     "major.png",
    "Капитан-лейтенант":         "captain_lieutenant.png",
    "Капитан":                   "captain.png",
    "Платиновый лейтенант":      "platinum_lieutenant.png",
    "Серебряный лейтенант":      "silver_lieutenant.png",
    "Сержант":                   "sergeant.png",
    "Прапорщик":                 "warrant_officer.png",
    "Рядовой":                   "private.png",
}




def save_last_clicked_city(city_name: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # если строки ещё нет, вставим, иначе перепишем
    cur.execute(
        "INSERT OR REPLACE INTO last_click (id, city_name) VALUES (1, ?)",
        (city_name,)
    )
    conn.commit()
    conn.close()


def load_cities_from_db(selected_kingdom):
    """
    Функция загружает данные о городах для выбранного княжества из таблицы city.

    :param selected_kingdom: Название выбранного княжества.
    :return: Список словарей с данными о городах.
    """
    # Подключение к базе данных
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Запрос к таблице city для получения данных по выбранному княжеству
        query = """
        SELECT id, kingdom, color, fortress_name, coordinates
        FROM city
        WHERE kingdom = ?
        """
        cursor.execute(query, (selected_kingdom,))
        rows = cursor.fetchall()

        # Преобразование данных в список словарей
        cities = []
        for row in rows:
            city_data = {
                'id': row[0],
                'kingdom': row[1],
                'color': row[2],
                'fortress_name': row[3],
                'coordinates': row[4]  # Предполагается, что координаты хранятся как строка "x,y"
            }
            cities.append(city_data)

        return cities

    except sqlite3.Error as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return []

    finally:
        # Закрытие соединения с базой данных
        conn.close()


def restore_from_backup():
    """
    Загрузка данных из стандартных таблиц (default) в рабочие таблицы.
    Используется при запуске новой игры для восстановления начального состояния.
    """
    # Настройка логирования
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Подключение к базе данных
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Список таблиц для восстановления
        tables_to_restore = [
            ("city_default", "city"),
            ("diplomacies_default", "diplomacies"),
            ("relations_default", "relations"),
            ("resources_default", "resources"),
            ("cities_default", "cities"),
            ("units_default", "units")
        ]

        # Проверяем существование всех стандартных таблиц
        all_tables_exist = True
        for default_table, _ in tables_to_restore:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (default_table,))
            if not cursor.fetchone():
                logging.error(f"Таблица {default_table} не найдена в базе данных.")
                all_tables_exist = False

        if not all_tables_exist:
            logging.error("Не все стандартные таблицы найдены. Восстановление невозможно.")
            return

        # Начало транзакции
        cursor.execute("BEGIN TRANSACTION")

        # Восстанавливаем данные из стандартных таблиц в рабочие
        for default_table, working_table in tables_to_restore:
            try:
                # Проверяем, есть ли данные в стандартной таблице
                cursor.execute(f"SELECT COUNT(*) FROM {default_table}")
                if cursor.fetchone()[0] == 0:
                    logging.warning(f"Стандартная таблица {default_table} пуста. Пропускаем восстановление.")
                    continue

                # Очищаем рабочую таблицу
                cursor.execute(f"DELETE FROM {working_table}")

                # Копируем данные из стандартной таблицы в рабочую
                cursor.execute(f'''
                    INSERT INTO {working_table}
                    SELECT * FROM {default_table}
                ''')
                logging.info(f"Данные успешно восстановлены из таблицы {default_table} в таблицу {working_table}.")
            except Exception as e:
                logging.error(f"Ошибка при восстановлении таблицы {working_table}: {e}")
                conn.rollback()  # Откатываем транзакцию в случае ошибки
                return

        # Фиксируем изменения
        conn.commit()
        logging.info("Все данные успешно восстановлены из стандартных таблиц.")

    except sqlite3.Error as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
        if conn:
            conn.rollback()  # Откатываем транзакцию в случае ошибки
    finally:
        if conn:
            conn.close()


def clear_tables(conn):
    """
    Очищает данные из указанных таблиц базы данных.
    :param conn: Подключение к базе данных SQLite.
    """
    tables_to_clear = [
        "buildings",
        "city",
        "diplomacies",
        "garrisons",
        "resources",
        "trade_agreements",
        "turn",
        "armies",
        "political_systems",
        "karma",
        "user_faction",
        "units",
        "experience",
        "queries",
        "results",
        "auto_build_settings"
    ]

    cursor = conn.cursor()

    try:
        for table in tables_to_clear:
            # Используем TRUNCATE или DELETE для очистки таблицы
            cursor.execute(f"DELETE FROM {table};")
            print(f"Таблица '{table}' успешно очищена.")

        # Фиксируем изменения
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при очистке таблиц: {e}")
        conn.rollback()  # Откат изменений в случае ошибки


class MapWidget(Widget):
    def __init__(self, selected_kingdom=None, player_kingdom=None, **kwargs):
        super(MapWidget, self).__init__(**kwargs)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.fortress_rectangles = []  # Список для хранения крепостей
        self.current_player_kingdom = player_kingdom  # Текущее королевство игрока

        # Настройки карты
        self.base_map_width = 1200  # Исходная ширина карты (px)
        self.base_map_height = 800  # Исходная высота карты (px)
        self.map_scale = self.calculate_scale()  # Масштаб под текущий экран
        self.map_pos = self.calculate_centered_position()  # Центрированная позиция

        # Отрисовка карты
        with self.canvas:
            self.map_image = Rectangle(
                source='files/map/map.png',
                pos=self.map_pos,
                size=(self.base_map_width * self.map_scale, self.base_map_height * self.map_scale)
            )

        # Отрисовка всех крепостей и дорог
        self.draw_fortresses()
        self.draw_roads()

        # Обновление каждую секунду
        Clock.schedule_interval(lambda dt: self.update_cities(), 1)

    def calculate_scale(self):
        """Рассчитывает масштаб карты под текущий экран"""
        scale_width = Window.width / self.base_map_width
        scale_height = Window.height / self.base_map_height
        return min(scale_width, scale_height) * 0.9  # Добавляем небольшой отступ

    def calculate_centered_position(self):
        """Вычисляет центрированную позицию карты"""
        scaled_width = self.base_map_width * self.map_scale
        scaled_height = self.base_map_height * self.map_scale
        x = (Window.width - scaled_width) / 2
        y = (Window.height - scaled_height) / 2
        return [x, y]

    def draw_roads(self):
        """Рисует дороги между ближайшими городами"""
        self.canvas.after.clear()

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT fortress_name, coordinates FROM city")
            fortresses_data = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке данных о городах: {e}")
            return

        cities = []
        for fortress_name, coords_str in fortresses_data:
            try:
                coords = ast.literal_eval(coords_str)
                if len(coords) == 2:
                    cities.append((fortress_name, coords))
            except (ValueError, SyntaxError) as e:
                print(f"Ошибка при разборе координат города '{fortress_name}': {e}")
                continue

        with self.canvas.after:
            Color(0.5, 0.5, 0.5, 1)  # Серый цвет для дорог

            for i in range(len(cities)):
                for j in range(i + 1, len(cities)):
                    source_name, source_coords = cities[i]
                    dest_name, dest_coords = cities[j]

                    # Вычисляем расстояние
                    total_diff = self.calculate_manhattan_distance(source_coords, dest_coords)

                    if total_diff < 224:  # Рисуем дорогу, если расстояние ≤ 220
                        # Вычисляем координаты с учётом масштаба и позиции
                        drawn_x1 = source_coords[0] * self.map_scale + self.map_pos[0]
                        drawn_y1 = source_coords[1] * self.map_scale + self.map_pos[1]
                        drawn_x2 = dest_coords[0] * self.map_scale + self.map_pos[0]
                        drawn_y2 = dest_coords[1] * self.map_scale + self.map_pos[1]

                        Line(points=[drawn_x1, drawn_y1, drawn_x2, drawn_y2], width=1)

    def calculate_manhattan_distance(self, source_coords, destination_coords):
        """Вычисляет манхэттенское расстояние между точками"""
        return abs(source_coords[0] - destination_coords[0]) + abs(source_coords[1] - destination_coords[1])

    def draw_fortresses(self):
        """Рисует крепости на карте и обновляет координаты иконок и названий в базе данных"""
        self.fortress_rectangles.clear()
        self.canvas.clear()

        with self.canvas:
            self.map_image = Rectangle(
                source='files/map/map.png',
                pos=self.map_pos,
                size=(self.base_map_width * self.map_scale, self.base_map_height * self.map_scale)
            )

            faction_images = {
                'Хиперион': 'files/buildings/giperion.png',
                'Аркадия': 'files/buildings/arkadia.png',
                'Селестия': 'files/buildings/celestia.png',
                'Этерия': 'files/buildings/eteria.png',
                'Халидон': 'files/buildings/halidon.png'
            }

            try:
                cursor = self.conn.cursor()
                cursor.execute("SELECT fortress_name, kingdom, coordinates FROM city")
                fortresses_data = cursor.fetchall()
            except sqlite3.Error as e:
                print(f"Ошибка при загрузке данных о городах: {e}")
                return

            if not fortresses_data:
                print("Нет данных о городах в базе данных.")
                return

            for fortress_name, kingdom, coords_str in fortresses_data:
                try:
                    coords = ast.literal_eval(coords_str)
                    if len(coords) == 2:
                        fort_x, fort_y = coords
                    else:
                        continue
                except (ValueError, SyntaxError) as e:
                    print(f"Ошибка при разборе координат города '{fortress_name}': {e}")
                    continue

                # Вычисляем позицию с учётом масштаба
                drawn_x = fort_x * self.map_scale + self.map_pos[0]
                drawn_y = fort_y * self.map_scale + self.map_pos[1]

                # Получаем путь к изображению
                image_path = faction_images.get(kingdom, 'files/buildings/default.png')
                if not os.path.exists(image_path):
                    image_path = 'files/buildings/default.png'

                # Сохраняем данные о крепости
                fort_rect = (drawn_x, drawn_y, 77, 77)
                self.fortress_rectangles.append((
                    fort_rect,
                    {"coordinates": (fort_x, fort_y), "name": fortress_name},
                    kingdom
                ))

                # Рисуем крепость
                Rectangle(source=image_path, pos=(drawn_x, drawn_y), size=(77, 77))

                # Добавляем название города
                display_name = fortress_name[:20] + "..." if len(fortress_name) > 20 else fortress_name
                label = CoreLabel(text=display_name, font_size=25, color=(0, 0, 0, 1))
                label.refresh()
                text_texture = label.texture
                text_width, text_height = text_texture.size
                text_x = drawn_x + (40 - text_width) / 2
                text_y = drawn_y - text_height - 5

                Color(1, 1, 1, 1)
                Rectangle(texture=text_texture, pos=(text_x, text_y), size=(text_width, text_height))

                # --- Записываем координаты в базу данных ---
                try:
                    cursor.execute("""
                        UPDATE cities
                        SET icon_coordinates = ?, label_coordinates = ?
                        WHERE name = ?
                    """, (
                        f"({drawn_x}, {drawn_y})",  # icon_coordinates
                        f"({text_x}, {text_y})",  # label_coordinates
                        fortress_name
                    ))
                    self.conn.commit()
                except sqlite3.Error as e:
                    print(f"Ошибка при обновлении координат для {fortress_name}: {e}")

    def check_fortress_click(self, touch):
        """Проверяет нажатие на крепость"""
        for fort_rect, fortress_data, owner in self.fortress_rectangles:
            x, y, w, h = fort_rect
            if x <= touch.x <= x + w and y <= touch.y <= y + h:
                save_last_clicked_city(fortress_data["name"])
                popup = FortressInfoPopup(
                    ai_fraction=owner,
                    city_coords=fortress_data["coordinates"],
                    player_fraction=self.current_player_kingdom
                )
                popup.open()
                print(
                    f"Крепость {fortress_data['coordinates']} принадлежит {'вашему' if owner == self.current_player_kingdom else 'чужому'} королевству!")
                break

    def on_touch_up(self, touch):
        """Обрабатывает нажатия на карту"""
        self.check_fortress_click(touch)

    def update_cities(self):
        """Обновляет отображение городов"""
        self.canvas.clear()
        self.draw_fortresses()


class RoundedButton(Button):
    instances = []  # Список всех созданных кнопок

    def __init__(self, bg_color=(0.1, 0.5, 0.9, 1), radius=25, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.radius = radius
        self.background_color = (0, 0, 0, 0)  # Отключаем стандартный фон
        self.active = False  # Состояние кнопки: активна ли она
        self.darken_factor = 0.8  # Коэффициент затемнения

        # Сохраняем инстанс кнопки
        RoundedButton.instances.append(self)

        with self.canvas.before:
            self.rect_color = Color(*self.bg_color)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[radius]
            )

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def darken_color(self, color, factor):
        return [c * factor for c in color[:3]] + list(color[3:])

    def on_press(self):
        # Сообщаем всем кнопкам, что эта активна
        self.set_active_button(self)

    def deactivate(self):
        self.active = False
        self.rect_color.rgba = self.bg_color

    def activate(self):
        self.active = True
        self.rect_color.rgba = self.darken_color(self.bg_color, self.darken_factor)

    @classmethod
    def set_active_button(cls, active_button):
        for btn in cls.instances:
            if btn == active_button:
                btn.activate()
            else:
                btn.deactivate()


class MenuWidget(FloatLayout):
    def __init__(self, **kwargs):
        super(MenuWidget, self).__init__(**kwargs)

        # ======== Фоновые изображения (попеременно сменяются) ========
        self.bg_image_1 = Image(
            source='files/menu/arkadia.jpg',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.bg_image_2 = Image(
            source='files/menu/celestia.jpg',
            allow_stretch=True,
            keep_ratio=False,
            opacity=0,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.add_widget(self.bg_image_1)
        self.add_widget(self.bg_image_2)

        # ======== Логотип / Заголовок ========
        self.title_label = Label(
            text="Лэрдон",
            font_size='48sp',
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            halign='center',
            valign='middle',
            size_hint=(0.6, 0.3),
            pos_hint={'center_x': 0.5, 'top': 1.05},
            markup=True
        )
        self.add_widget(self.title_label)

        # ======== Создаём кнопки, но оставляем их невидимыми (opacity=0) ========
        # При помощи pos_hint задаём вертикальные «якоря» (y-координаты),
        # чтобы потом просто менять opacity.
        self.btn_start_game = RoundedButton(
            text="В Лэрдон",
            size_hint=(0.4, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.68},
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp',
            opacity=0
        )
        self.btn_dossier = RoundedButton(
            text="Личное дело",
            size_hint=(0.4, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.53},
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp',
            opacity=0
        )
        self.btn_how_to_play = RoundedButton(
            text="Как играть",
            size_hint=(0.4, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.38},
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp',
            opacity=0
        )
        self.btn_author = RoundedButton(
            text="Автор",
            size_hint=(0.4, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.23},
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp',
            opacity=0
        )
        self.btn_exit = RoundedButton(
            text="Выход",
            size_hint=(0.4, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.07},
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp',
            opacity=0
        )

        # ======== Привязываем обработчики нажатий ========
        self.btn_start_game.bind(on_release=self.start_game)
        self.btn_dossier.bind(on_release=self.open_dossier)
        self.btn_how_to_play.bind(on_release=self.open_how_to_play)
        self.btn_author.bind(on_release=self.open_author)
        self.btn_exit.bind(on_release=self.exit_game)

        # ======== Добавляем кнопки в виджет ========
        self.add_widget(self.btn_start_game)
        self.add_widget(self.btn_dossier)
        self.add_widget(self.btn_how_to_play)
        self.add_widget(self.btn_author)
        self.add_widget(self.btn_exit)

        # ======== По таймеру запускаем появление кнопок ========
        Clock.schedule_once(self.animate_buttons_in, 0.5)

        # ======== Анимация смены фоновых картинок каждые 5 секунд ========
        self.current_image = self.bg_image_1
        self.next_image = self.bg_image_2
        Clock.schedule_interval(self.animate_background, 5)

    def animate_buttons_in(self, dt):
        """
        Последовательно увеличиваем opacity для каждой кнопки,
        чтобы они «появлялись» сверху вниз.
        """
        self.buttons_locked = True
        buttons = [
            self.btn_start_game,
            self.btn_dossier,
            self.btn_how_to_play,
            self.btn_author,
            self.btn_exit
        ]
        delay_between = 0.2  # задержка между появлением соседних кнопок

        for index, btn in enumerate(buttons):
            # Для каждого btn через index * delay_between запускаем анимацию opacity=1
            Clock.schedule_once(
                lambda dt, widget=btn: Animation(opacity=1, duration=0.4).start(widget),
                index * delay_between
            )

        # Когда появится последняя кнопка, разблокируем все кнопки
        total_delay = (len(buttons) - 1) * delay_between + 0.4
        Clock.schedule_once(lambda dt: setattr(self, 'buttons_locked', False), total_delay)

    def animate_background(self, dt):
        """
        Фоновая подмена изображений с плавным переходом.
        """
        new_source = random.choice([
            'files/menu/arkadia.jpg',
            'files/menu/celestia.jpg',
            'files/menu/eteria.jpg',
            'files/menu/halidon.jpg',
            'files/menu/giperion.jpg'
        ])
        # гарантируем, что источник изменится:
        while new_source == self.next_image.source:
            new_source = random.choice([
                'files/menu/arkadia.jpg',
                'files/menu/celestia.jpg',
                'files/menu/eteria.jpg',
                'files/menu/halidon.jpg',
                'files/menu/giperion.jpg'
            ])

        self.next_image.source = new_source
        fade_out = Animation(opacity=0, duration=1.5)
        fade_in = Animation(opacity=1, duration=1.5)
        fade_out.start(self.current_image)
        fade_in.start(self.next_image)
        # меняем указатели, чтобы следующий раз фейдить к другой картинке
        self.current_image, self.next_image = self.next_image, self.current_image

    # === Обработчики перехода между экранами ===

    def open_dossier(self, instance):
        if getattr(self, 'buttons_locked', False):
            return
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(DossierScreen())

    def open_how_to_play(self, instance):
        if getattr(self, 'buttons_locked', False):
            return
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(HowToPlayScreen())

    def open_author(self, instance):
        if getattr(self, 'buttons_locked', False):
            return
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(AuthorScreen())

    def start_game(self, instance):
        if getattr(self, 'buttons_locked', False):
            return
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(KingdomSelectionWidget())

    def exit_game(self, instance):
        App.get_running_app().stop()


class CustomTab(TabbedPanelItem):
    def __init__(self, **kwargs):
        super(CustomTab, self).__init__(**kwargs)
        self.active_color = get_color_from_hex('#FF5733')   # например, оранжевый
        self.inactive_color = get_color_from_hex('#DDDDDD')  # светло-серый
        self.background_color = self.inactive_color
        self.bind(state=self.update_background)

    def update_background(self, *args):
        if self.state == 'down':
            self.background_color = self.active_color
        else:
            self.background_color = self.inactive_color


class DossierScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_clear_event = None
        self.auto_clear_toggle = None
        self.tabs = None
        # Построение UI делаем в on_kv_post или прямо в __init__.
        self.build_ui()

    def build_ui(self):
        """
        Основной метод, собирающий весь интерфейс:
        - Заголовок
        - TabbedPanel, растягивающийся по оставшемуся пространству
        - Нижняя панель кнопок
        """
        root_layout = BoxLayout(orientation='vertical')

        # === Заголовок "Личное дело" ===
        title_widget = self._create_title_bar()
        root_layout.add_widget(title_widget)

        # === TabbedPanel ===
        # Убираем size_hint_y=None и фиксированную высоту. Вместо этого делаем size_hint=(1, 1)
        self.tabs = TabbedPanel(do_default_tab=False, size_hint=(1, 1))
        # Сразу загружаем данные — внутри load_dossier_data() каждая вкладка будет содержать ScrollView
        self.load_dossier_data()
        root_layout.add_widget(self.tabs)

        # === Нижняя панель кнопок ===
        bottom_panel = self._create_bottom_panel()
        # Нижняя панель остаётся фиксированной по высоте
        root_layout.add_widget(bottom_panel)

        self.add_widget(root_layout)

    def _create_title_bar(self):
        """
        Создаёт BoxLayout с заливкой фона и границами, а внутри Label.
        Возвращает готовый виджет.
        """
        title_box = BoxLayout(size_hint_y=None, height=dp(60))
        with title_box.canvas.before:
            Color(0.1, 0.1, 0.1, 0.95)
            bg_rect = Rectangle(size=title_box.size, pos=title_box.pos)
            Color(0, 0.7, 1, 1)
            border_line = Line(
                rectangle=(title_box.x + 1, title_box.y + 1, title_box.width - 2, title_box.height - 2),
                width=1.4
            )

        # При изменении размеров/позиции обновляем Rect и Line
        def _update_title_canvas(instance, _):
            bg_rect.size = instance.size
            bg_rect.pos = instance.pos
            border_line.rectangle = (
                instance.x + 1,
                instance.y + 1,
                instance.width - 2,
                instance.height - 2
            )

        title_box.bind(pos=_update_title_canvas, size=_update_title_canvas)

        title_label = Label(
            text="[b]Личное дело[/b]",
            markup=True,
            font_size=sp(24),
            color=get_color_from_hex('#FFD700'),
            halign='center',
            valign='middle'
        )
        title_box.add_widget(title_label)
        return title_box

    def _create_bottom_panel(self):
        """
        Создаёт нижнюю панель с кнопками:
        - «Назад»
        - «Очистить»
        """
        bottom = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10))

        # Кнопка «Назад»
        back_btn = Button(
            text="Назад в главное меню",
            background_color=(0, 0.7, 1, 1),
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16)
        )
        back_btn.bind(on_release=self.go_back)
        bottom.add_widget(back_btn)

        # Кнопка «Очистить данные»
        clear_btn = Button(
            text="Очистить данные",
            background_color=(0.9, 0.2, 0.2, 1),
            size_hint_y=None,
            height=dp(48),
            font_size=sp(16)
        )
        clear_btn.bind(on_release=self.clear_dossier)
        bottom.add_widget(clear_btn)

        return bottom


    def load_dossier_data(self):
        """
        Читает данные из SQLite и наполняет TabbedPanel.
        Если данных нет — выводит таб «Информация» с надписью «Ваше личное дело не найдено в архиве»
        Если данные есть — группирует по фракциям и создаёт для каждой фракции вкладку.
        """
        # Очищаем предыдущие вкладки, если они уже были
        if self.tabs.get_tab_list():
            for tab in list(self.tabs.get_tab_list()):
                self.tabs.remove_widget(tab)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM dossier")
            rows = cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")
            rows = []
        finally:
            conn.close()

        if not rows:
            # Если записей нет
            info_label = Label(
                text="Ваше личное дело не найдено в архиве",
                font_size=sp(18),
                color=get_color_from_hex('#FFFFFF'),
                halign='center'
            )
            tab = TabbedPanelItem(text="Информация")
            tab.add_widget(info_label)
            self.tabs.add_widget(tab)
            return

        # Группируем по фракциям (предполагаем, что row[1] — это фракция)
        factions = {}
        for row in rows:
            faction = row[1]
            data = {
                'military_rank': row[2],
                'avg_military_rating': row[3],
                'avg_soldiers_starving': row[4],
                'victories': row[5],
                'defeats': row[6],
                'matches_won': row[7],
                'matches_lost': row[8],
                'last_data': row[9]
            }
            factions.setdefault(faction, []).append(data)

        # Для каждой фракции создаём новую вкладку
        for faction, data_list in factions.items():
            tab = CustomTab(text=faction)
            scroll = ScrollView()
            grid = GridLayout(
                cols=2,
                spacing=dp(10),
                padding=dp(10),
                size_hint_y=None
            )
            grid.bind(minimum_height=grid.setter('height'))

            for data in data_list:
                card = self._create_character_card(data)
                grid.add_widget(card)

            scroll.add_widget(grid)
            tab.add_widget(scroll)
            self.tabs.add_widget(tab)

    def _create_character_card(self, data: dict) -> BoxLayout:
        """
        Создаёт одну карточку «персонажа»:
        1) Загружает иконку звания через resource_find, переводя русское звание в английское имя файла,
        2) Под картинкой — текст звания (по-прежнему на русском),
        3) Дальше — статистика (военный рейтинг, голод, результаты и т.д.).
        Высота card подгоняется автоматически под содержимое.
        """
        total_height = 0

        # --- 1. Корневой контейнер карточки ---
        card = BoxLayout(
            orientation='vertical',
            size_hint_y=None,  # высоту задаём вручную
            spacing=dp(5),
            padding=dp(5)
        )

        # Фон и рамка у карточки
        with card.canvas.before:
            Color(0.15, 0.15, 0.15, 1)
            bg_rect = Rectangle(size=card.size, pos=card.pos)
            Color(0.3, 0.3, 0.3, 1)
            border_line = Line(
                rectangle=(card.x + 1, card.y + 1, card.width - 2, card.height - 2),
                width=1
            )

        def _update_card_canvas(instance, _):
            bg_rect.size = instance.size
            bg_rect.pos = instance.pos
            border_line.rectangle = (
                instance.x + 1,
                instance.y + 1,
                instance.width - 2,
                instance.height - 2
            )

        card.bind(pos=_update_card_canvas, size=_update_card_canvas)

        # === 2. Собираем "сырой" rank и нормализуем только для отладки/поиска файла ===
        raw_rank = data.get('military_rank') or "Рядовой"
        rank = raw_rank.strip()
        rank = unicodedata.normalize("NFC", rank)
        # Заменяем все возможные тире/дефисы на обычный ASCII-дефис,
        # чтобы ключ точно совпал с RANK_TO_FILENAME
        rank = (
            rank
            .replace("\u2010", "-")
            .replace("\u2011", "-")
            .replace("\u2012", "-")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2015", "-")
        )

        # --- 3. Выбираем английское имя файла из словаря, если нет — fallback на 'private.png' ---
        filename = RANK_TO_FILENAME.get(rank, "private.png")
        asset_path = f"files/menu/dossier/{filename}"

        # Логируем, что ищем и что нашли
        Logger.debug(f"myapp: raw_rank={raw_rank!r}, normalized rank={rank!r}")
        Logger.debug(f"myapp: Ожидаемое имя файла: {filename!r}")
        Logger.debug(f"myapp: Ищу resource_find({asset_path!r}) →")
        real_path = resource_find(asset_path)
        Logger.debug(f"myapp: resource_find вернул: {real_path!r}")

        # === 4. Рисуем контейнер для иконки ===
        image_height = dp(90)
        image_container = BoxLayout(size_hint_y=None, height=image_height, padding=dp(5))

        if real_path:
            rank_img = Image(
                source=real_path,
                size_hint=(None, None),
                size=(dp(60), dp(60))
            )
        else:
            # Если иконка не найдена (на всякий случай), показываем знак вопроса
            rank_img = Label(text="?", font_size=sp(30), color=(1, 1, 1, 0.5))

        img_anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        img_anchor.add_widget(rank_img)
        image_container.add_widget(img_anchor)
        card.add_widget(image_container)
        total_height += image_height

        # === 5. Текстовое (русское) звание под иконкой ===
        rank_label_height = dp(30)
        rank_label = Label(
            text=f"[b]{raw_rank}[/b]",  # <-- отображаем именно raw_rank, без перевода
            markup=True,
            font_size=sp(18),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint=(None, None),
            size=(self.width, rank_label_height)
        )
        rank_anchor = AnchorLayout(
            anchor_x='center',
            anchor_y='top',
            size_hint_y=None,
            height=rank_label_height
        )
        rank_anchor.add_widget(rank_label)
        card.add_widget(rank_anchor)
        total_height += rank_label_height

        # === 6. Левый блок: военный рейтинг и голод ===
        left_label_height = dp(50)
        left_text = (
            f"[b]Военный рейтинг(ср.):[/b] {data.get('avg_military_rating', 0)}\n"
            f"[b]Умерло войск от голода(ср.):[/b] {data.get('avg_soldiers_starving', 0)}"
        )
        left_label = Label(
            text=left_text,
            markup=True,
            font_size=sp(14),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=left_label_height
        )
        card.add_widget(left_label)
        total_height += left_label_height

        # === 7. Правый блок: сражения и матчи ===
        right_label_height = dp(50)
        right_text = (
            f"[b]Сражения (В/П):[/b]\n"
            f"[color=#00FF00]{data.get('victories', 0)}[/color]/"
            f"[color=#FF0000]{data.get('defeats', 0)}[/color]\n"
            f"[b]Матчи (В/П):[/b]\n"
            f"[color=#00FF00]{data.get('matches_won', 0)}[/color]/"
            f"[color=#FF0000]{data.get('matches_lost', 0)}[/color]"
        )
        right_label = Label(
            text=right_text,
            markup=True,
            font_size=sp(14),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=right_label_height
        )
        card.add_widget(right_label)
        total_height += right_label_height

        # === 8. Дата последней игры ===
        date_label_height = dp(20)
        date_label = Label(
            text=f"Последняя игра: {data.get('last_data', '-')} ",
            font_size=sp(12),
            color=get_color_from_hex('#AAAAAA'),
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=date_label_height
        )
        card.add_widget(date_label)
        total_height += date_label_height

        # Устанавливаем итоговую высоту карточки
        card.height = total_height + dp(10)
        return card

    def clear_dossier(self, instance):
        """
        Полная очистка всех записей в таблице dossier.
        После успеха — полностью удаляем и пересоздаем вкладку.
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM dossier")
            conn.commit()
            print("✅ Все записи успешно удалены.")
        except sqlite3.Error as e:
            print(f"❌ Ошибка удаления: {e}")
        finally:
            conn.close()

        self._recreate_dossier_tab()

    def go_back(self, instance):
        """
        Переход обратно в главное меню: удаляем все виджеты корня и добавляем MenuWidget.
        """
        app = App.get_running_app()
        root = app.root
        root.clear_widgets()
        root.add_widget(MenuWidget())

    def _recreate_dossier_tab(self):
        """
        Полностью удаляет текущую вкладку 'Личное дело' и создаёт новую.
        """
        # Определяем, какая вкладка сейчас открыта
        current_tab = self.tabs.current_tab

        # Если это нужная нам вкладка — удаляем её
        if current_tab and current_tab.text == "Информация":
            self.tabs.remove_widget(current_tab)

        # Перезагружаем данные и создаём новую вкладку
        self.load_dossier_data()
        tab_list = self.tabs.get_tab_list()
        if tab_list:
            self.tabs.switch_to(tab_list[0])

class HowToPlayScreen(FloatLayout):
    def __init__(self, **kwargs):
        super(HowToPlayScreen, self).__init__(**kwargs)
        # Фон
        self.add_widget(Image(source='files/menu/how_to_play_bg.jpg', allow_stretch=True, keep_ratio=False))

        # Панель вкладок
        self.tab_panel = TabbedPanel(
            do_default_tab=False,
            size_hint=(0.8, 0.6),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # === Вкладка "Экономика" ===
        economy_content = self.create_scrollable_content([
            {"type": "text", "content": "Экономика....всмысле налоги высокие? плати давай\n\n"
                                        "Первое и главное что нужно сделать на первом же ходу — это определить "
                                        "соотношение построек между больницами и фабриками.\n"
                                        "Они очень сильно влияют на экономику и дальнейшее развитие. "
                                        "Экспериментируйте с соотношением только тогда, когда уже научились играть.\n\n"
                                        "Стандартное решение для всех фракций — это 2 больницы на 1 фабрику. Такое "
                                        "соотношение никогда не приведёт к сильному упадку экономики на старте, "
                                        "а недостаток крон можно компенсировать продав сырьё на рынке(вкладка торговля тут же)."},
            {"type": "image", "source": "files/menu/tutorial/economy_1.jpg"},
            {"type": "text", "content": "Так же стоит установить сразу налоги(на продаже сырья пока его мало, далеко "
                                        "не уедешь, а враг не дремлет) Итак рекомендую 34% налога.(размер налога "
                                        "влияет на то любит вас население или нет(будет от вас убегать или наоборот "
                                        "прибывать)) Если выставить слишком большие налоги все разбегутся и Ваше государство прекратит существование(Вы проиграете))"},
            {"type": "image", "source": "files/menu/tutorial/economy_2.jpg"},
            {"type": "text", "content": "* Для более детальной информации об экономике игры посетите раздел схема"}
        ])

        # === Вкладка "Армия" ===
        army_content = self.create_scrollable_content([
            {"type": "text", "content": "Управление армией — какой дебил нас сюда послал...\n\n"
                                        "Начнем с того что набирать юнитов по принципу чем больше тем лучше -> плохая идея.\n"
                                        "Заботитесь о качестве вашей армии, а не о ее численности. Иначе сожрут лимит, а толку мало\n"
                                        "Итак базовые моменты, в игре есть атакующие юниты и защитные.(определяется по текущим характеристикам юнита)"},
            {"type": "image", "source": "files/menu/tutorial/army_1.jpg"},
            {"type": "text", "content": "На примере выше видно, как выглядит карточка юнита.\n"
                                        "Пробежимся по ключевым моментам:\n"
                                        "\n"
                                        "Урон - взаимодействует с классом юнита(чем выше класс тем выше урон(доп. "
                                        "коэфициент увеличения урона)) - учитывается при атаке на город противника\n"
                                        "\n"
                                        "Защита - учитывается при защите города и складывается с Живучестью, увеличивая параметр защиты.\n"
                                        "\n"
                                        "Класс - увеличивает базовый урон юнита и определяет очередность вступания в бой.\n"
                                        "Первыми в бой вступают самые младшие классы города(1 самый младший 5 самый старший в игре).\n"
                                        "Если у тебя в гарнизоне несколько юнитов с одинаковым классом то первый в бой вступает тот у которого больше урон\n"
                                        "Таким образом нужно учитывать это при атаке или защите города(будут ли "
                                        "защитные юниты защищать атакующих юнитов гарнизона при отражении атаки "
                                        "врага? И кто первым будет "
                                        "атаковать врага в городе? не дай бог это будут защитные юниты они там "
                                        "полягут все)"
                                        "\n"
                                        "Ниже рассмотрим как управлять армией"},
            {"type": "image", "source": "files/menu/tutorial/army_2.jpg"},
            {"type": "text", "content": "После того как ты набрал юнитов, можешь их разместить в одном из городов \n"
                                        "Разместить армию - это как раз та кнопка которая размещает войска в городе \n"
                                        "Ввести войска - это отправка войск из других городов(то есть уже размещенные войска) в текущий \n"
                                        "Хочешь напасть? Нажимай ввести войска и выбирай далее кем хочешь напасть. "
                                        "Важно! Перемещение происходит группами\n"
                                        "То есть ты должен как быть 'Набрать группу из юнитов' это может быть даже "
                                        "один юнит и далее ты отправляешь группу в текущий город\n"
                                        "тоже самое если ты хочешь перебазировать войска из одного города в другой \n"
                                        "КЛЮЧЕВОЕ ЧТО НАДО УЧИТЫВАТЬ У ТЕБЯ ВСЕГО ОДНО ПЕРЕМЕЩЕНИЕ НА ХОД! \n"
                                        "Если напал на врага - ты израсходовал перемещение \n"
                                        "Если перевел войска из одного своего города в другой - ты израсходовал перемещение \n"
                                        "Атака на город врага провалилась? - ты израсходовал перемещение \n"
                                        "\n"
                                        "Не маловажный момент имеет логистика, ты не можешь нападать на любой город на карте из любой точки, только в ближайший \n"
                                        "НО если ты перемещаешь войска между своими городами то тут логистика не имеет значения,"
                                        " ты моментально можешь переместить войска из одной части карты в другую \n"
                                        "\n"
                                        "Будь осторожен игрок! И помни вся твоя навоеванная статистика учитывается в финальном отчете!"}
        ])

        # === Вкладка "Политика" ===
        politics_content = self.create_scrollable_content([
            {"type": "text", "content": "Политика...че вы начинаете? нормально же общались!.\n\n"
                                        "Итак первое что надо сделать на первом же ходу выяснить кто ты Коммунист или "
                                        "Капиталист?.\n"
             },
            {"type": "image", "source": "files/menu/tutorial/politic_1.jpg"},
            {"type": "text", "content": "Там выбираем полит. строй и видим:"},
            {"type": "image", "source": "files/menu/tutorial/politic_2.jpg"},
            {"type": "text", "content": "Коммунист - увеличение производства сырья (на самом деле бафф/дэбафф, "
                                        "если идешь в минус то это добавит сверху)\n"
                                        "Капиталист - увеличение уровня дохода крон (та же херня, не удивляйся "
                                        "откуда у тебя такой минус в деньгах при капитализме если доходы "
                                        "отрицательные)\n"
                                        "Ну и мое любимое, одни ненавидят других, а значит рано или поздно дадут друг "
                                        "друг в репу. \n"
                                        "При этом ты всегда можешь 'переобуться', видишь как твоих друзей уничтожают "
                                        "капиталисты? Ну что ж теперь я тоже капиталист и наоборот. \n"
                                        "Чтобы тебе захотели набить лицо у тебя должны быть \n"
                                        "1. Плохие отношения с ними, возможно потому что ты из другого 'лагеря'(они "
                                        "ухудшаются постоянно).\n"
                                        "2. Слабая армия\n"
                                        "Только одновременно два этих условия дают повод врагам атаковать тебя.\n"
                                        "Тебя могут 'терпеть' до тех пор пока у тебя сильная армия\n"
                                        "Но это не значит что твои друзья могут стать врагами если у тебя слабая "
                                        "армия это не так.\n"
                                        "Вы в одной команде? даже если у тебя слабая армия мы тебя не тронем потому "
                                        "что ты свой в доску. \n"
                                        "Так же обрати внимание на соседние вкладки этого окна например Отношения(Тут "
                                        "можно отслеживать как 'Хорошо' у тебя обстоят дела с другими странами)"},
            {"type": "image", "source": "files/menu/tutorial/politic_3.jpg"},
            {"type": "text", "content": "Здесь мы видим как к нам относятся и готовы ли с нами выгодно торговать(ну "
                                        "то есть бартер).\n"
                                        "Колонка Кф. торговли влияет на выгодность сделок между тобой и страной с "
                                        "которой ты хочешь заключить торговое соглашение\n"
                                        "(Особенно полезно когда на рынке цены упали на 'дно шахты', и ты хочешь "
                                        "сделку повыгоднее) \n "
                                        "\n"
                                        "Перейдем к следующему большому разделу который тоже имеет отношение к дипломатии.\n"
                                        ""},
            {"type": "image", "source": "files/menu/tutorial/politic_4.jpg"},
            {"type": "image", "source": "files/menu/tutorial/politic_5.jpg"},
            {"type": "text", "content": "Тут мы видим стандартный набор договоров:\n\n"
                                        "Торговое соглашение - обмен ресурсами на условиях которые предусмотрены "
                                        "отношениями. \n"
                                        "например Кф. 1.5 дает возможность условно предлагать 10, а требовать 15 "
                                        "любого ресурса.\n"
                                        "Договор об культурном обмене - проще говоря лизать задницу другому "
                                        "государству чтобы улучшить с ним отношения \n"
                                        "Заключение мира - тут все ясно, если ты предлагаешь мир и ты сильнее при "
                                        "этом то они согласятся на мир а если слабее...тоо...не пошел бы...\n"
                                        "Заключение альянса - можно заключить союз с страной с которой у тебя хорошие "
                                        "отношения(куча ништяков типо попрашайничества ресурсов войск(помощь в "
                                        "защите) и даже возможность приказать развязать войну с другим государством("
                                        "например помочь тебе отмудохать кое кого))\n"
                                        "Но учти любой запрос к союзнику идет долго и помощь приходит не сразу, "
                                        "войска на следующий ход, а ресурсы через один ход\n"
                                        "Чтобы 'попользовать' союзника выбери вкладку Союзник рядом с Дипломатией. \n"
                                        "Затем чтобы отдать приказ об обороне, выбери защита и город который тебе "
                                        "надо защитить(просто нажми на него) \n"
                                        "Если хочешь отдать приказ об атаке на врага делай тоже самое, выбирай атака "
                                        "и город противника.\n"
                                        "Объявление войны - тут аккуратнее, если не вытянешь войну потом сложно будет "
                                        "помириться."},
        ])

        economy_scheme_content = self.create_scrollable_content([
            {"type": "text", "content": "Разберём подробнее, как работает экономическая система Лэрдона:\n\n"
                                        "Если по простому то тут все от чего-то зависит..."},

            {"type": "image", "source": "files/menu/tutorial/shema.png"},
            {"type": "text", "content": "Больницы производят рабочих, но потребляют кроны\n"
                                        "Фабрики требуют рабочих, но вырабатывают сырье\n"
                                        "Население растет от прироста рабочих, размера налогов(если низкие) и наличия сырья(без него идет "
                                        "сокращение населения), но добавляют кроны в казну(если налоги установлены)\n"
                                        "Армия так же требует наличия сырья и активно его потребляет вместе с "
                                        "населением, однако если потребление войск превысит лимит армии, то каждый "
                                        "ход значительная часть армии будет "
                                        "умирать от голода. Пока ее потребление снова не станет меньше или равно лимиту"}
        ])

        # === Вкладка "Экономика" ===
        economy_tab = TabbedPanelHeader(text='Экономика')
        economy_tab.content = economy_content
        economy_tab.size_hint_x = None
        economy_tab.width = Window.width * 0.8 / 4  # ~ 1/4 ширины панели
        self.tab_panel.add_widget(economy_tab)

        # === Вкладка "Армия" ===
        army_tab = TabbedPanelHeader(text='Армия')
        army_tab.content = army_content
        army_tab.size_hint_x = None
        army_tab.width = Window.width * 0.8 / 4
        self.tab_panel.add_widget(army_tab)

        # === Вкладка "Политика" ===
        politics_tab = TabbedPanelHeader(text='Политика')
        politics_tab.content = politics_content
        politics_tab.size_hint_x = None
        politics_tab.width = Window.width * 0.8 / 4
        self.tab_panel.add_widget(politics_tab)

        # === Вкладка "Схема экономики" ===
        economy_scheme_tab = TabbedPanelHeader(text='Схема')
        economy_scheme_tab.content = economy_scheme_content
        economy_scheme_tab.size_hint_x = None
        economy_scheme_tab.width = Window.width * 0.8 / 4
        self.tab_panel.add_widget(economy_scheme_tab)
        # Добавляем вкладки на экран
        self.add_widget(self.tab_panel)
        # Кнопка "Вернуться в главное меню"
        back_button = Button(
            text="Вернуться в главное меню",
            size_hint=(0.4, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.05},
            background_normal='',
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size='16sp'
        )
        back_button.bind(on_press=self.back_to_menu)
        self.add_widget(back_button)

    def create_scrollable_content(self, content_blocks):
        layout = BoxLayout(orientation='vertical', size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        for block in content_blocks:
            if block["type"] == "text":
                label = Label(
                    text=block["content"],
                    halign='left',
                    valign='top',
                    size_hint_y=None,
                    font_size='16sp',
                    text_size=(None, None)  # Сначала не задаем ширину
                )

                # Правильное использование bind с учётом двух аргументов
                def update_text_size(lbl, value):
                    lbl.text_size = (lbl.width, None)
                    lbl.height = lbl.texture_size[1]  # Обновляем высоту под текст

                label.bind(
                    width=update_text_size,
                    texture_size=lambda lbl, value: lbl.setter('height')(lbl, value[1])
                )

                layout.add_widget(label)

            elif block["type"] == "image":
                img = Image(
                    source=block["source"],
                    size_hint=(None, None),
                    width=Window.width * 0.8,
                    height=Window.width * 0.45,
                    allow_stretch=True,
                    keep_ratio=False
                )
                layout.add_widget(img)

        scroll_view = ScrollView(size_hint=(1, 1), do_scroll_x=False, scroll_y=1)
        scroll_view.add_widget(layout)

        # Прокрутка вверх через небольшую задержку
        Clock.schedule_once(lambda dt: setattr(scroll_view, 'scroll_y', 1), 0.1)

        return scroll_view

    def back_to_menu(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(MenuWidget())


class KingdomSelectionWidget(FloatLayout):
    def __init__(self, **kwargs):
        super(KingdomSelectionWidget, self).__init__(**kwargs)
        is_android = platform == 'android'

        # Инициализируем selected_button
        self.selected_button = None

        # ======== ФОН ВИДЕО ========
        self.bg_video = Video(
            source='files/menu/choice.mp4',
            state='play',
            options={'eos': 'loop'},
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.bg_video.bind(on_eos=self.loop_video)
        self.add_widget(self.bg_video)

        # ======== ЗАГОЛОВОК «Выберите сторону» ========
        label_size = '36sp' if is_android else '40sp'
        self.select_side_label = Label(
            text="Выберите сторону",
            font_size=label_size,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            markup=True,
            halign='center',
            valign='middle',
            size_hint=(0.8, None),
            height=dp(80) if is_android else 80,
            pos_hint={'center_x': 0.75, 'top': 0.97}
        )
        self.add_widget(self.select_side_label)

        # ======== ИНФО О ФРАКЦИИ ========
        self.faction_info_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.15, None),
            height=dp(120),
            pos_hint={'center_x': 0.73, 'center_y': 0.4},
            spacing=dp(8)
        )
        self.add_widget(self.faction_info_container)

        # ======== ИЗОБРАЖЕНИЕ СОВЕТНИКА ========
        advisor_size = (0.3, 0.3)
        self.advisor_image = Image(
            source='files/null.png',
            size_hint=advisor_size,
            pos_hint={'center_x': 0.75, 'center_y': 0.6}
        )
        self.add_widget(self.advisor_image)

        # ======== КОНТЕЙНЕР ДЛЯ КНОПОК ========
        self.buttons_container = FloatLayout()
        self.add_widget(self.buttons_container)

        # ======== ЗАГРУЗКА ДАННЫХ ИЗ БД ========
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.kingdom_data = self.load_kingdoms_from_db()

        # ======== ПАНЕЛЬ КНОПОК ФРАКЦИЙ (изначально скрыта) ========
        panel_width = 0.35
        button_height = dp(45) if is_android else 60
        spacing_val = dp(10) if is_android else 10
        padding = [dp(20), dp(20), dp(20), dp(20)] if is_android else [20, 20, 20, 20]

        total_height = self.calculate_panel_height(button_height, spacing_val, padding)

        # Здесь смещаем начальную позицию по Y чуть выше (0.6 вместо 0.5):
        initial_y = Window.height * 0.6 - total_height / 2

        self.kingdom_buttons = BoxLayout(
            orientation='vertical',
            spacing=spacing_val,
            size_hint=(panel_width, None),
            height=total_height,
            pos=(-Window.width * 0.7, initial_y),  # был 0.5, заменили на 0.6
            opacity=1
        )

        for kingdom in self.kingdom_data.keys():
            btn = RoundedButton(
                text=kingdom,
                size_hint_y=None,
                height=button_height,
                font_size='18sp' if is_android else '16sp',
                color=(1, 1, 1, 1),
                bg_color=(0.1, 0.5, 0.9, 1),
                opacity=0
            )
            btn.bind(on_release=self.select_kingdom)
            self.kingdom_buttons.add_widget(btn)

        self.buttons_container.add_widget(self.kingdom_buttons)

        # ======== КНОПКА «Начать игру» (сразу видна) ========
        self.start_game_button = RoundedButton(
            text="Начать игру",
            size_hint=(0.3, None),
            height=button_height,
            font_size='18sp' if is_android else '16sp',
            bold=True,
            color=(1, 1, 1, 1),
            bg_color=(0.2, 0.8, 0.2, 1),
            pos_hint={'center_x': 0.75, 'y': 0.1},
            opacity=1
        )
        self.start_game_button.bind(on_release=self.start_game)
        self.buttons_container.add_widget(self.start_game_button)

        # ======== КНОПКА «Вернуться в главное меню» (сразу видна) ========
        self.back_btn = RoundedButton(
            text="Вернуться в главное меню",
            size_hint=(0.34, 0.08),
            pos_hint={'x': 0.005, 'y': 0.05},
            color=(1, 1, 1, 1),
            font_size='16sp',
            bg_color=(0.8, 0.2, 0.2, 1),
            opacity=1
        )
        self.back_btn.bind(on_release=self.back_to_menu)
        self.buttons_container.add_widget(self.back_btn)

        # ======== Запускаем анимацию появления кнопок-фракций ========
        Clock.schedule_once(lambda dt: self.animate_in(), 0.3)

    def animate_in(self):
        """
        1) Ставим панель в финальную позицию (выше),
        2) Поочерёдно проявляем opacity каждой кнопки-фракции,
        3) Кнопки «Начать игру» и «Вернуться» уже видны.
        """
        # Смещаем финальную позицию панели по Y (тоже выше):
        final_x_panel = Window.width * 0.1
        final_y_panel = Window.height * 0.6 - self.kingdom_buttons.height / 2  # было 0.5, заменили на 0.6
        self.kingdom_buttons.pos = (final_x_panel, final_y_panel)

        # Список всех кнопок-фракций внутри BoxLayout, сверху вниз:
        faction_buttons = list(self.kingdom_buttons.children)[::-1]
        delay_between = 0.15

        for idx, btn in enumerate(faction_buttons):
            Clock.schedule_once(
                lambda dt, widget=btn: Animation(opacity=1, duration=0.4).start(widget),
                idx * delay_between
            )

        total_delay = (len(faction_buttons) - 1) * delay_between + 0.4
        self.buttons_locked = True
        Clock.schedule_once(lambda dt: setattr(self, 'buttons_locked', False), total_delay)


    def loop_video(self, instance):
        instance.state = 'stop'
        instance.state = 'play'

    def calculate_panel_height(self, btn_height, spacing, padding):
        num_buttons = len(self.kingdom_data)
        return (btn_height * num_buttons) + (spacing * (num_buttons - 1)) + (padding[1] + padding[3])

    def back_to_menu(self, instance):
        if getattr(self, 'buttons_locked', False):
            return
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(MenuWidget())

    def load_kingdoms_from_db(self):
        kingdoms = {}
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT kingdom, fortress_name, coordinates, color FROM city_default")
            rows = cursor.fetchall()
            for row in rows:
                kingdom, fortress_name, coordinates, color = row
                if kingdom not in kingdoms:
                    kingdoms[kingdom] = {"fortresses": [], "color": color}
                kingdoms[kingdom]["fortresses"].append({"name": fortress_name, "coordinates": coordinates})
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке данных из базы данных: {e}")
        return kingdoms

    def select_kingdom(self, instance):
        if getattr(self, 'buttons_locked', False):
            return

        kingdom_name = instance.text
        kingdom_info = self.kingdom_data[kingdom_name]

        # Подсветка выбранной кнопки
        if not hasattr(instance, "original_color"):
            instance.original_color = instance.rect_color.rgba
        if self.selected_button:
            self.selected_button.rect_color.rgba = self.selected_button.original_color

        rgba_color = self.hex_to_rgba(kingdom_info["color"])
        instance.rect_color.rgba = rgba_color
        self.selected_button = instance

        # Обновляем образ советника
        kingdom_rename = {
            "Аркадия": "arkadia",
            "Селестия": "celestia",
            "Этерия": "eteria",
            "Хиперион": "giperion",
            "Халидон": "halidon"
        }
        app = App.get_running_app()
        app.selected_kingdom = kingdom_name
        eng = kingdom_rename.get(kingdom_name, kingdom_name).lower()
        adv_path = f'files/sov/sov_{eng}.jpg'
        if os.path.exists(adv_path):
            self.advisor_image.source = adv_path
            self.advisor_image.reload()

        # Обновляем инфо-панель:
        self.get_kingdom_info(kingdom_name)

    def hex_to_rgba(self, hex_color):
        # Вставьте здесь свою логику конвертации
        return (0, 0.3, 0.4, 1)

    def generate_icons_layout(self, value, max_value=3):
        layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20))
        for i in range(max_value):
            img_path = 'files/pict/menu/full.png' if i < value else 'files/pict/menu/grey.png'
            img = Image(source=img_path, size_hint=(None, None), size=('16dp', '16dp'))
            layout.add_widget(img)
        return layout

    def get_kingdom_info(self, kingdom):
        full_img = 'files/pict/menu/full.png'
        empty_img = 'files/pict/menu/grey.png'
        if not os.path.exists(full_img) or not os.path.exists(empty_img):
            return

        stats = {
            "Аркадия": {"Доход крон": 3, "Доход сырья": 1, "Армия": 2},
            "Селестия": {"Доход крон": 2, "Доход сырья": 2, "Армия": 2},
            "Хиперион": {"Доход крон": 2, "Доход сырья": 2, "Армия": 3},
            "Халидон": {"Доход крон": 1, "Доход сырья": 3, "Армия": 1},
            "Этерия": {"Доход крон": 1, "Доход сырья": 2, "Армия": 2}
        }
        data = stats.get(kingdom)
        if not data:
            return

        self.faction_info_container.clear_widgets()
        crown_row = BoxLayout(size_hint_y=None, height=dp(20))
        crown_row.add_widget(Label(text="Доход крон:", size_hint_x=None, width=dp(100)))
        crown_row.add_widget(self.generate_icons_layout(data["Доход крон"]))
        self.faction_info_container.add_widget(crown_row)

        resource_row = BoxLayout(size_hint_y=None, height=dp(20))
        resource_row.add_widget(Label(text="Доход сырья:", size_hint_x=None, width=dp(100)))
        resource_row.add_widget(self.generate_icons_layout(data["Доход сырья"]))
        self.faction_info_container.add_widget(resource_row)

        army_row = BoxLayout(size_hint_y=None, height=dp(20))
        army_row.add_widget(Label(text="Армия:", size_hint_x=None, width=dp(100)))
        army_row.add_widget(self.generate_icons_layout(data["Армия"]))
        self.faction_info_container.add_widget(army_row)

    def start_game(self, instance):
        if getattr(self, 'buttons_locked', False):
            return

        if not getattr(self, 'selected_button', None):
            print("Фракция не выбрана.")
            return

        # === Блокируем все кнопки ===
        self.disable_all_buttons(True)

        # === Создаём Overlay и запускаем видео ===
        overlay = FloatLayout(size=Window.size)
        self.overlay = overlay
        self.add_widget(overlay)

        self.start_video = Video(
            source='files/menu/start_game.mp4',
            state='play',
            options={'eos': 'stop'},
            allow_stretch=True,
            keep_ratio=False,
            size=Window.size,
            pos=(0, 0)
        )
        overlay.add_widget(self.start_video)

        # Привязываем on_eos, чтобы при окончании видео сразу запустить игру:
        self.start_video.bind(on_eos=self.on_start_video_end)

        # Резервный таймер на 3 секунды, если on_eos по какой-то причине не сработает:
        Clock.schedule_once(self.force_start_game, 3)

    def on_start_video_end(self, instance, value):
        # Когда видео завершено (или state == 'stop'), начинаем игру
        if value or (self.start_video and self.start_video.state == 'stop'):
            print("Видео завершено (on_eos), начинаем игру...")
            self.cleanup_and_start_game()

    def force_start_game(self, dt):
        # Если on_eos не сработал за 3 сек, форсируем запуск игры
        print("Резервный таймер сработал — завершаем видео и запускаем игру")
        if self.start_video:
            self.start_video.state = 'stop'
        self.cleanup_and_start_game()

    def cleanup_and_start_game(self):
        # Убираем оверлей с видео
        if hasattr(self, 'overlay') and self.overlay in self.children:
            self.remove_widget(self.overlay)
        self.disable_all_buttons(False)

        try:
            conn = sqlite3.connect(db_path)
            clear_tables(conn)
            conn.close()
            restore_from_backup()

            app = App.get_running_app()
            selected_kingdom = app.selected_kingdom
            cities = load_cities_from_db(selected_kingdom)
            if not cities:
                print("Города не найдены.")
                return

            game_screen = GameScreen(selected_kingdom, cities, db_path=db_path)
            app.root.clear_widgets()
            map_widget = MapWidget(selected_kingdom=selected_kingdom, player_kingdom=selected_kingdom)
            app.root.add_widget(map_widget)
            app.root.add_widget(game_screen)
        except Exception as e:
            print(f"Ошибка при запуске игры: {e}")

    def disable_all_buttons(self, disabled=True):
        for child in self.buttons_container.walk():
            if isinstance(child, RoundedButton):
                child.disabled = disabled


class EmpireApp(App):
    def __init__(self, **kwargs):
        super(EmpireApp, self).__init__(**kwargs)
        # Флаг, что мы на мобильной платформе Android
        self.is_mobile = (platform == 'android')
        # Можно завести другие глобальные настройки здесь
        self.selected_kingdom = None  # Атрибут для хранения выбранного королевства

    def build(self):
        return LoadingScreen() # Возвращаем виджет главного меню

    def restart_app(self):
        # Явное закрытие всех соединений с базой данных
        conn = sqlite3.connect(db_path)
        clear_tables(conn)
        conn.close()

        # Восстановление из бэкапа
        restore_from_backup()

        # Сброс состояния приложения
        self.selected_kingdom = None

        # Полная очистка корневого виджета
        self.root.clear_widgets()

        # Пересоздание главного меню
        Clock.schedule_once(self.recreate_main_menu, 0.2)

    def recreate_main_menu(self, dt):
        self.root.add_widget(MenuWidget())
        print("Главное меню полностью пересоздано")

    def on_stop(self):
        # Закрываем все соединения при завершении
        for child in self.root.children:
            if hasattr(child, 'conn'):
                child.conn.close()


if __name__ == '__main__':
    EmpireApp().run()  # Запуск приложения
