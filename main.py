from lerdon_libraries import *
from game_process import GameScreen
from ui import *

# Размеры окна
screen_width, screen_height = 1200, 800

# Путь к БД
# === Настройка пути к базе данных ===
if platform == 'android':
    from android.storage import app_storage_path

    storage_dir = app_storage_path()
else:
    storage_dir = os.path.dirname(__file__)

original_db_path = os.path.join(os.path.dirname(__file__), 'game_data.db')
copied_db_path = os.path.join(storage_dir, 'game_data.db')

# Копируем БД, если её нет в пользовательской директории
if not os.path.exists(copied_db_path):
    if os.path.exists(original_db_path):
        import shutil

        shutil.copy(original_db_path, copied_db_path)
        print(f"✅ База данных скопирована в {copied_db_path}")
    else:
        raise FileNotFoundError(f"❌ game_data.db отсутствует в проекте!")

# Теперь можно подключаться к БД
db_path = copied_db_path
print("✅ Используем БД по пути:", db_path)


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


def cleanup_sqlite_cache(db_path):
    """
    Удаляет .shm и .wal файлы, если они старше 5 минут.
    """
    shm_file = db_path + "-shm"
    wal_file = db_path + "-wal"

    for cache_file in [shm_file, wal_file]:
        if os.path.exists(cache_file):
            # Получаем время последнего изменения файла
            file_mtime = os.path.getmtime(cache_file)
            age_seconds = time.time() - file_mtime
            if age_seconds > 300:  # 5 минут = 300 секунд
                try:
                    os.remove(cache_file)
                    print(f"🗑️ Удалён устаревший файл кэша: {cache_file}")
                except Exception as e:
                    print(f"❌ Не удалось удалить файл {cache_file}: {e}")


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
        """Рисует крепости на карте"""
        self.fortress_rectangles.clear()
        self.canvas.clear()

        # Перерисовываем карту
        with self.canvas:
            self.map_image = Rectangle(
                source='files/map/map.png',
                pos=self.map_pos,
                size=(self.base_map_width * self.map_scale, self.base_map_height * self.map_scale)
            )

            # Словарь фракций и их изображений
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

            # Рисуем крепости
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

        # Фон
        self.bg_image_1 = Image(source='files/menu/arkadia.jpg', allow_stretch=True, keep_ratio=False)
        self.bg_image_2 = Image(source='files/menu/celestia.jpg', allow_stretch=True, keep_ratio=False, opacity=0)
        self.add_widget(self.bg_image_1)
        self.add_widget(self.bg_image_2)

        # Логотип
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
            pos_hint={'center_x': 0.5, 'top': 0.98},
            markup=True
        )
        self.add_widget(self.title_label)

        # Кнопки (изначально вне экрана)
        self.btn_start_game = RoundedButton(
            text="В Лэрдон",
            size_hint=(0.4, 0.08),
            pos=(-400, Window.height * 0.68),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp'
        )
        self.btn_how_to_play = RoundedButton(
            text="Как играть",
            size_hint=(0.4, 0.08),
            pos=(-400, Window.height * 0.53),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp'
        )
        self.btn_exit = RoundedButton(
            text="Выход",
            size_hint=(0.4, 0.08),
            pos=(-400, Window.height * 0.38),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size='20sp'
        )

        # Привязываем действия
        self.btn_start_game.bind(on_press=self.start_game)
        self.btn_how_to_play.bind(on_press=self.open_how_to_play)
        self.btn_exit.bind(on_press=self.exit_game)

        # Добавляем кнопки на экран
        self.add_widget(self.btn_start_game)
        self.add_widget(self.btn_how_to_play)
        self.add_widget(self.btn_exit)

        # Анимация появления кнопок
        Clock.schedule_once(self.animate_buttons_in, 0.5)

        # Анимация фона
        self.current_image = self.bg_image_1
        self.next_image = self.bg_image_2
        Clock.schedule_interval(self.animate_background, 5)

    def animate_buttons_in(self, dt):
        # Анимация: кнопки выезжают с левой стороны
        anim1 = Animation(x=Window.width * 0.5 - self.btn_start_game.width / 2, y=Window.height * 0.68, duration=0.6, t='out_back')
        anim2 = Animation(x=Window.width * 0.5 - self.btn_how_to_play.width / 2, y=Window.height * 0.53, duration=0.6, t='out_back')
        anim3 = Animation(x=Window.width * 0.5 - self.btn_exit.width / 2, y=Window.height * 0.38, duration=0.6, t='out_back')

        anim1.start(self.btn_start_game)
        anim2.start(self.btn_how_to_play)
        anim3.start(self.btn_exit)

    def animate_background(self, dt):
        new_source = random.choice([
            'files/menu/arkadia.jpg',
            'files/menu/celestia.jpg',
            'files/menu/eteria.jpg',
            'files/menu/halidon.jpg',
            'files/menu/giperion.jpg'
        ])
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
        self.current_image, self.next_image = self.next_image, self.current_image

    def open_how_to_play(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(HowToPlayScreen())

    def start_game(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(KingdomSelectionWidget())

    def exit_game(self, instance):
        App.get_running_app().stop()

# Вкладка обучения
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

        # === Статичные элементы (фон, заголовок, информация, советник) ===
        # Фон - видео
        self.bg_video = Video(
            source='files/menu/choice.mp4',
            state='play',
            options={'eos': 'loop'}  # Может сработать в некоторых реализациях
        )
        self.bg_video.allow_stretch = True
        self.bg_video.keep_ratio = False
        self.bg_video.size = Window.size
        self.bg_video.bind(on_eos=self.loop_video)  # Ловим конец видео
        self.add_widget(self.bg_video)

        # Заголовок
        label_size = '20sp' if is_android else '36sp'
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
            height=dp(60) if is_android else 80,
            pos_hint={'center_x': 0.5, 'top': 0.9}
        )
        self.add_widget(self.select_side_label)

        # Информация о фракции
        self.faction_info_container = BoxLayout(
            orientation='vertical',
            size_hint=(0.2, None),
            height=dp(120),
            pos_hint={'center_x': 0.73, 'center_y': 0.4},
            spacing=dp(8)
        )
        self.add_widget(self.faction_info_container)

        # Советник
        advisor_size = (0.3, 0.3) if is_android else (0.25, 0.25)
        self.advisor_image = Image(
            source='files/null.png',
            size_hint=advisor_size,
            pos_hint={'center_x': 0.75, 'center_y': 0.6}
        )
        self.add_widget(self.advisor_image)

        # === Анимируемый блок (только кнопки) ===
        self.buttons_container = FloatLayout()
        self.add_widget(self.buttons_container)

        # Подключение к базе данных
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.kingdom_data = self.load_kingdoms_from_db()

        # === Новые атрибуты для подсветки фракции ===
        self.selected_button = None

        # Панель кнопок (выезжает слева)
        panel_width = 0.3
        button_height = dp(50) if is_android else 60
        spacing_val = dp(10) if is_android else 10
        padding = [dp(20), dp(20), dp(20), dp(20)] if is_android else [20, 20, 20, 20]

        self.kingdom_buttons = BoxLayout(
            orientation='vertical',
            spacing=spacing_val,
            size_hint=(panel_width, None),
            height=self.calculate_panel_height(button_height, spacing_val, padding),
            pos=(-Window.width * 0.5, self.center_y * 2.4)
        )

        for kingdom in self.kingdom_data.keys():
            btn = RoundedButton(
                text=kingdom,
                size_hint_y=None,
                height=button_height,
                font_size='18sp' if is_android else '16sp',
                color=(1, 1, 1, 1),
                bg_color=(0.1, 0.5, 0.9, 1)
            )
            btn.bind(on_press=self.select_kingdom)
            self.kingdom_buttons.add_widget(btn)

        self.buttons_container.add_widget(self.kingdom_buttons)

        # Кнопка "Начать игру" (появляется справа)
        self.start_game_button = RoundedButton(
            text="Начать игру",
            size_hint=(0.3, None),
            height=button_height,
            font_size='18sp' if is_android else '16sp',
            bold=True,
            color=(1, 1, 1, 1),
            bg_color=(0.1, 0.5, 0.9, 1),
            pos=(Window.width * 1.2, Window.height * 0.1)
        )
        self.start_game_button.bind(on_press=self.start_game)
        self.buttons_container.add_widget(self.start_game_button)

        # Кнопка "Вернуться в главное меню"
        back_btn = RoundedButton(
            text="Вернуться в главное меню",
            size_hint=(0.34, 0.08),
            pos=(Window.width * 0.005, Window.height * 0.05),
            color=(1, 1, 1, 1),
            font_size='16sp',
            bg_color=(0.1, 0.5, 0.9, 1)
        )
        back_btn.bind(on_press=self.back_to_menu)
        self.buttons_container.add_widget(back_btn)

        # Анимация появления только кнопок
        Clock.schedule_once(lambda dt: self.animate_in(), 0.3)

    def loop_video(self, instance):
        print("Видео закончилось, перезапускаем...")
        instance.state = 'stop'
        instance.state = 'play'

    def animate_in(self):
        center_x = Window.width * 0.5
        center_y = Window.height * 0.5

        # Панель фракций — выезжает слева
        anim_panel = Animation(
            x=center_x - self.kingdom_buttons.width / 1.4,
            y=center_y * 0.4,
            duration=0.6,
            t='out_back'
        )
        anim_panel.start(self.kingdom_buttons)

        # Кнопка "Начать игру" — появляется справа
        anim_start = Animation(
            x=center_x + self.kingdom_buttons.width / 2 + dp(30),
            y=Window.height * 0.1,
            duration=0.6,
            t='out_back'
        )
        anim_start.start(self.start_game_button)

        # Кнопка "Вернуться в главное меню" — выезжает слева
        back_btn = self.children[-1]
        anim_back = Animation(
            x=center_x - back_btn.width / 2,
            y=Window.height * 0.001,
            duration=0.6,
            t='out_back'
        )
        anim_back.start(back_btn)

    def calculate_panel_height(self, btn_height, spacing, padding):
        num_buttons = len(self.kingdom_data)
        return (btn_height * num_buttons) + (spacing * (num_buttons - 1)) + (padding[1] + padding[3])

    def back_to_menu(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(MenuWidget())

    def load_kingdoms_from_db(self):
        kingdoms = {}
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT kingdom, fortress_name, coordinates, color FROM city_default")
            rows = cursor.fetchall()
            print(f"Загружено записей из city_default: {len(rows)}")
            for row in rows:
                kingdom, fortress_name, coordinates, color = row
                if kingdom not in kingdoms:
                    kingdoms[kingdom] = {"fortresses": [], "color": color}
                kingdoms[kingdom]["fortresses"].append({"name": fortress_name, "coordinates": coordinates})
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке данных из базы данных: {e}")
        return kingdoms

    def select_kingdom(self, instance):
        kingdom_name = instance.text
        kingdom_info = self.kingdom_data[kingdom_name]

        # Сохраняем оригинальный цвет
        if not hasattr(instance, "original_color"):
            instance.original_color = instance.rect_color.rgba

        # Сбрасываем предыдущую кнопку
        if self.selected_button:
            self.selected_button.rect_color.rgba = self.selected_button.original_color

        # Применяем новый цвет
        faction_color = kingdom_info["color"]
        rgba_color = self.hex_to_rgba(faction_color)
        instance.rect_color.rgba = rgba_color
        self.selected_button = instance

        # Обновляем данные интерфейса
        kingdom_rename = {
            "Аркадия": "arkadia",
            "Селестия": "celestia",
            "Этерия": "eteria",
            "Хиперион": "giperion",
            "Халидон": "halidon"
        }
        app = App.get_running_app()
        app.selected_kingdom = kingdom_name
        english_name = kingdom_rename.get(kingdom_name, kingdom_name).lower()
        advisor_image_path = f'files/sov/sov_{english_name}.jpg'
        self.advisor_image.source = advisor_image_path
        self.advisor_image.reload()

        # === ОБНОВЛЕНИЕ: вызываем метод, который заполняет self.faction_label через Image() ===
        self.get_kingdom_info(kingdom_name)

    def hex_to_rgba(self, hex_color):
        return (0, 0.3, 0.4, 1)

    def generate_icons_layout(self, value, max_value=3):
        layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='20dp')
        for i in range(max_value):
            img_path = 'files/pict/menu/full.png' if i < value else 'files/pict/menu/grey.png'
            img = Image(source=img_path, size_hint=(None, None), size=('16dp', '16dp'))
            layout.add_widget(img)
        return layout

    def get_kingdom_info(self, kingdom):
        full_img = 'files/pict/menu/full.png'
        empty_img = 'files/pict/menu/grey.png'

        if not os.path.exists(full_img) or not os.path.exists(empty_img):
            print("❌ Один или оба файла изображений отсутствуют!")
            return self.get_fallback_kingdom_info(kingdom)

        stats = {
            "Аркадия": {"Доход крон": 3, "Доход сырья": 1, "Армия": 2},
            "Селестия": {"Доход крон": 2, "Доход сырья": 2, "Армия": 2},
            "Хиперион": {"Доход крон": 2, "Доход сырья": 2, "Армия": 3},
            "Халидон": {"Доход крон": 1, "Доход сырья": 3, "Армия": 1},
            "Этерия": {"Доход крон": 1, "Доход сырья": 2, "Армия": 2}
        }

        data = stats.get(kingdom)
        if not data:
            return ""

        # Чистим старый контент
        self.faction_info_container.clear_widgets()

        # Заголовок: Название фракции — больше и левее
        title_label = Label(
            text=f"[b]{kingdom}[/b]",
            markup=True,
            font_size='20sp' if platform == 'android' else '24sp',  # ← Больше текст
            size_hint_y=None,
            height=dp(10),
            halign='left',
            valign='middle',
            text_size=(None, dp(40))
        )
        self.faction_info_container.add_widget(title_label)

        # Доход крон
        crown_row = BoxLayout(size_hint_y=None, height=dp(20))
        crown_row.add_widget(Label(text="Доход крон:", size_hint_x=None, width=dp(100)))
        crown_row.add_widget(self.generate_icons_layout(data["Доход крон"]))
        self.faction_info_container.add_widget(crown_row)

        # Доход сырья
        resource_row = BoxLayout(size_hint_y=None, height=dp(20))
        resource_row.add_widget(Label(text="Доход сырья:", size_hint_x=None, width=dp(100)))
        resource_row.add_widget(self.generate_icons_layout(data["Доход сырья"]))
        self.faction_info_container.add_widget(resource_row)

        # Армия
        army_row = BoxLayout(size_hint_y=None, height=dp(20))
        army_row.add_widget(Label(text="Армия:", size_hint_x=None, width=dp(100)))
        army_row.add_widget(self.generate_icons_layout(data["Армия"]))
        self.faction_info_container.add_widget(army_row)

    def start_game(self, instance):
        conn = sqlite3.connect(db_path)
        clear_tables(conn)
        conn.close()
        restore_from_backup()
        app = App.get_running_app()
        selected_kingdom = app.selected_kingdom
        if not selected_kingdom:
            print("Фракция не выбрана.")
            return
        cities = load_cities_from_db(selected_kingdom)
        if not cities:
            print("Города не найдены.")
            return
        game_screen = GameScreen(selected_kingdom, cities, db_path=db_path)
        app.root.clear_widgets()
        map_widget = MapWidget(selected_kingdom=selected_kingdom, player_kingdom=selected_kingdom)
        app.root.add_widget(map_widget)
        app.root.add_widget(game_screen)

# Основное приложение
class EmpireApp(App):
    def __init__(self, **kwargs):
        super(EmpireApp, self).__init__(**kwargs)
        # Флаг, что мы на мобильной платформе Android
        self.is_mobile = (platform == 'android')
        # Можно завести другие глобальные настройки здесь
        self.selected_kingdom = None  # Атрибут для хранения выбранного королевства

    def build(self):
        return MenuWidget()  # Возвращаем виджет главного меню

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

        # Очистка устаревших файлов SQLite (.shm, .wal)
        cleanup_sqlite_cache(copied_db_path)


if __name__ == '__main__':
    cleanup_sqlite_cache(copied_db_path)
    EmpireApp().run()  # Запуск приложения
