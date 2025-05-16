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
                print(f"Крепость {fortress_data['coordinates']} принадлежит {'вашему' if owner == self.current_player_kingdom else 'чужому'} королевству!")
                break

    def on_touch_up(self, touch):
        """Обрабатывает нажатия на карту"""
        self.check_fortress_click(touch)

    def update_cities(self):
        """Обновляет отображение городов"""
        self.canvas.clear()
        self.draw_fortresses()




class MenuWidget(FloatLayout):
    def __init__(self, **kwargs):
        super(MenuWidget, self).__init__(**kwargs)

        # Список с именами файлов картинок и соответствующими фракциями
        self.menu_images = {
            'files/menu/arkadia.jpg': "Аркадия",
            'files/menu/celestia.jpg': "Селестия",
            'files/menu/eteria.jpg': "Этерия",
            'files/menu/halidon.jpg': "Халидон",
            'files/menu/giperion.jpg': "Хиперион"
        }

        # Создаем два изображения для плавной смены фона
        self.bg_image_1 = Image(source=random.choice(list(self.menu_images.keys())), allow_stretch=True, keep_ratio=False)
        self.bg_image_2 = Image(source=random.choice(list(self.menu_images.keys())), allow_stretch=True, keep_ratio=False, opacity=0)

        # Добавляем оба изображения на виджет
        self.add_widget(self.bg_image_1)
        self.add_widget(self.bg_image_2)

        # Заголовок
        self.title = Label(
            text="[b][color=FFFFFF]Лэрдон[/color][/b]",
            font_size='40sp',
            markup=True,
            size_hint=(1, 0.2),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            color=(1, 1, 1, 1)  # Белый текст
        )
        self.add_widget(self.title)

        # Кнопки
        button_height = 0.1
        button_spacing = 0.02  # Уменьшенное расстояние между кнопками
        button_start_y = 0.6  # Начальная позиция по Y для первой кнопки

        btn_start_game = Button(
            text="В Лэрдон",
            size_hint=(0.5, button_height),
            pos_hint={'center_x': 0.5, 'center_y': button_start_y},
            background_normal='',
            background_color=(0.2, 0.6, 1, 1),  # Голубой цвет
            color=(1, 1, 1, 1)  # Белый текст
        )
        btn_start_game.bind(on_press=self.start_game)

        btn_how_to_play = Button(
            text="Как играть",
            size_hint=(0.5, button_height),
            pos_hint={'center_x': 0.5, 'center_y': button_start_y - (button_height + button_spacing)},
            background_normal='',
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1)
        )
        btn_how_to_play.bind(on_press=self.open_how_to_play)
        self.add_widget(btn_how_to_play)

        btn_exit = Button(
            text="Выход",
            size_hint=(0.5, button_height),
            pos_hint={'center_x': 0.5, 'center_y': button_start_y - 2 * (button_height + button_spacing)},
            background_normal='',
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1)
        )
        btn_exit.bind(on_press=self.exit_game)

        # Добавляем кнопки
        self.add_widget(btn_start_game)
        self.add_widget(btn_exit)

        # Запускаем анимацию фона
        self.current_image = self.bg_image_1
        self.next_image = self.bg_image_2
        Clock.schedule_interval(self.animate_background, 5)  # Меняем фон каждые 5 секунд

        # Цвета для заголовка в зависимости от фракции
        self.faction_colors = {
            "Аркадия": (0, 0, 1, 1),  # Синий
            "Хиперион": (0.5, 0, 0.5, 1),  # Фиолетовый
            "Халидон": (1, 0, 0, 1),  # Красный
            "Этерия": (1, 1, 0, 1),  # Желтый
            "Селестия": (0, 0.5, 0, 1)  # Темно-зеленый
        }

        # Пример: изменение цвета заголовка при старте игры
        self.change_title_color("Аркадия")  # Можно заменить на текущую фракцию игрока

    def open_how_to_play(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(HowToPlayScreen())

    def animate_background(self, dt):
        """Анимация плавной смены фоновых изображений."""
        # Выбираем новое случайное изображение
        new_image_source = random.choice(list(self.menu_images.keys()))
        while new_image_source == self.next_image.source:  # Избегаем повторения текущего изображения
            new_image_source = random.choice(list(self.menu_images.keys()))
        self.next_image.source = new_image_source
        self.next_image.opacity = 0  # Начинаем с прозрачности 0

        # Анимация растворения старого изображения
        fade_out = Animation(opacity=0, duration=2)
        fade_out.start(self.current_image)

        # Анимация появления нового изображения
        fade_in = Animation(opacity=1, duration=2)
        fade_in.start(self.next_image)

        # Меняем местами current_image и next_image
        self.current_image, self.next_image = self.next_image, self.current_image

        # Определяем фракцию для нового изображения
        faction = self.menu_images[new_image_source]
        self.change_title_color(faction)

    def start_game(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(KingdomSelectionWidget())

    def exit_game(self, instance):
        App.get_running_app().stop()

    def change_title_color(self, faction):
        """
        Изменяет цвет заголовка "Лэрдон" в зависимости от фракции.
        :param faction: Название фракции
        """
        color = self.faction_colors.get(faction, (1, 1, 1, 1))  # По умолчанию белый
        self.title.color = color
        self.title.text = f"[b][color={self.rgb_to_hex(color)}]Лэрдон[/color][/b]"

    def rgb_to_hex(self, rgba):
        """
        Преобразует RGB(A) кортеж в шестнадцатеричный формат для Kivy.
        :param rgba: Кортеж (R, G, B, A)
        :return: Шестнадцатеричная строка (например, "#FFFFFF")
        """
        r, g, b, _ = rgba
        return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


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


# Виджет выбора княжества
class KingdomSelectionWidget(FloatLayout):
    def __init__(self, **kwargs):
        super(KingdomSelectionWidget, self).__init__(**kwargs)
        is_android = platform == 'android'
        # Подключение к базе данных
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.kingdom_data = self.load_kingdoms_from_db()
        # === Новые атрибуты для подсветки фракции ===
        self.selected_button = None  # Хранит ссылку на последнюю выбранную кнопку
        self.default_button_color = (0.1, 0.5, 0.9, 1)  # Цвет кнопок по умолчанию
        # Фон выбора княжества
        self.add_widget(Image(source='files/choice.jpg', allow_stretch=True, keep_ratio=False))

        # === Заголовок ===
        label_size = '20sp' if is_android else '10sp'
        self.select_side_label = Label(
            text="Выберите сторону",
            font_size=label_size,
            size_hint=(None, None),
            size=(300, 60) if is_android else (500, 350),
            pos_hint={'center_x': 0.75, 'center_y': 0.85},
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            markup=True
        )
        self.add_widget(self.select_side_label)

        # === Надпись с названием фракции ===
        faction_label_size = '14sp' if is_android else '24sp'
        self.faction_label = Label(
            text="",
            font_size=faction_label_size,
            size_hint=(None, None),
            size=(250, 100) if is_android else (300, 100),
            pos_hint={'center_x': 0.75, 'center_y': 0.30},
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            markup=True,
            halign="center",
            valign="middle"
        )
        self.faction_label.bind(size=self.faction_label.setter('text_size'))
        self.add_widget(self.faction_label)

        # === Панель кнопок ===
        # Настройки для Android
        if is_android:
            button_height = dp(50)  # Высота кнопок
            button_font_size = '18sp'  # Крупный шрифт
            panel_width = 0.4  # Шире панель для удобства
            spacing_val = dp(15)  # Уменьшаем промежуток
            padding = [dp(20), dp(20), dp(20), dp(20)]  # Отступы
        else:
            button_height = 60
            button_font_size = '14sp'
            panel_width = 0.4
            spacing_val = 15
            padding = [20, 20, 20, 20]

        self.kingdom_buttons = BoxLayout(
            orientation='vertical',
            spacing=spacing_val,
            size_hint=(panel_width, None),  # Фиксируем ширину, гибкая высота
            pos_hint={'center_x': 0.4, 'center_y': 0.5},
            padding=padding,
            height=self.calculate_panel_height(button_height, spacing_val, padding)
        )

        for kingdom in self.kingdom_data.keys():
            btn = Button(
                text=kingdom,
                size_hint_y=None,  # Фиксированная высота кнопок
                height=button_height,
                font_size=button_font_size,
                background_normal='',
                background_color=(0.1, 0.5, 0.9, 1),
                color=(1, 1, 1, 1),
                border=(dp(20), dp(20), dp(20), dp(20)),
                halign='center',
                valign='middle'
            )
            btn.bind(on_press=self.select_kingdom)
            btn.bind(on_enter=lambda x: Animation(background_color=(0.2, 0.6, 1, 1), duration=0.2).start(x))
            btn.bind(on_leave=lambda x: Animation(background_color=(0.1, 0.5, 0.9, 1), duration=0.2).start(x))
            self.kingdom_buttons.add_widget(btn)

        self.add_widget(self.kingdom_buttons)

        # === Изображение советника ===
        advisor_size = (0.3, 0.3) if is_android else (0.3, 0.3)
        advisor_pos = {'center_x': 0.75, 'center_y': 0.6}
        self.advisor_image = Image(
            source='files/null.png',
            size_hint=advisor_size,
            pos_hint=advisor_pos
        )
        self.add_widget(self.advisor_image)
        # Кнопка "Вернуться в главное меню"
        back_button = Button(
            text=" Вернуться в главное меню",
            size_hint=(0.34, 0.08),
            pos_hint={'center_x': 0.15, 'y': 0},
            background_normal='',
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size='16sp'
        )
        back_button.bind(on_press=self.back_to_menu)
        self.add_widget(back_button)

        # === Кнопка "Начать игру" ===
        start_btn_size = (0.3, None)
        start_btn_height = dp(50) if is_android else 60
        start_btn_font = '15sp' if is_android else '14sp'

        self.start_game_button = Button(
            text="Начать игру",
            size_hint=start_btn_size,
            height=start_btn_height,
            font_size=start_btn_font,
            bold=True,
            pos_hint={'center_x': 0.8, 'center_y': 0.10},
            background_normal='',
            background_color=(0.1, 0.5, 0.9, 1),
            color=(1, 1, 1, 1),
            border=(20, 20, 20, 20)
        )
        self.start_game_button.bind(on_press=self.start_game)
        self.start_game_button.bind(
            on_enter=lambda x: Animation(background_color=(0.2, 0.6, 1, 1), duration=0.2).start(x))
        self.start_game_button.bind(
            on_leave=lambda x: Animation(background_color=(0.1, 0.5, 0.9, 1), duration=0.2).start(x))
        self.add_widget(self.start_game_button)

    def calculate_panel_height(self, btn_height, spacing, padding):
        """Рассчитывает общую высоту панели кнопок"""
        num_buttons = len(self.kingdom_data)
        return (btn_height * num_buttons) + (spacing * (num_buttons - 1)) + (padding[1] + padding[3])

    def back_to_menu(self, instance):
        app = App.get_running_app()
        app.root.clear_widgets()
        app.root.add_widget(MenuWidget())

    def load_kingdoms_from_db(self):
        """Загружает данные о княжествах из базы данных."""
        kingdoms = {}
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT kingdom, fortress_name, coordinates, color
                FROM city_default
            """)
            rows = cursor.fetchall()
            print(f"Загружено записей из city_default: {len(rows)}")
            for row in rows:
                kingdom, fortress_name, coordinates, color = row
                if kingdom not in kingdoms:
                    kingdoms[kingdom] = {
                        "fortresses": [],
                        "color": color
                    }
                kingdoms[kingdom]["fortresses"].append({
                    "name": fortress_name,
                    "coordinates": coordinates
                })
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке данных из базы данных: {e}")
        return kingdoms

    def select_kingdom(self, instance):
        """Метод для обработки выбора княжества с подсветкой кнопки"""
        kingdom_name = instance.text
        kingdom_info = self.kingdom_data[kingdom_name]

        # === Сохраняем текущий цвет кнопки, если он ещё не сохранен ===
        if not hasattr(instance, "original_color"):
            instance.original_color = instance.background_color

        # === Если есть предыдущая выбранная кнопка, восстанавливаем её цвет ===
        if self.selected_button:
            self.selected_button.background_color = self.default_button_color

        # === Устанавливаем цвет кнопки в соответствии с фракцией ===
        faction_color = kingdom_info["color"]  # Цвет фракции из БД (например, "#0000FF")
        rgba_color = self.hex_to_rgba(faction_color)  # Преобразуем в RGBA
        instance.background_color = rgba_color
        self.selected_button = instance  # Обновляем ссылку на выбранную кнопку

        # === Остальной код метода без изменений ===
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

        faction_info_text = self.get_kingdom_info(kingdom_name)
        self.faction_label.text = f"[b]{kingdom_name}[/b]\n{faction_info_text}"

    def hex_to_rgba(self, hex_color):
        return (0, 0.3, 0.4, 1)  # Красный (fallback)

    def get_kingdom_info(self, kingdom):
        info = {
            "Аркадия": "Доход крон: 10\nДоход сырья: 5\nАрмия: 9\n",
            "Селестия": "Доход крон: 8\nДоход сырья: 6\nАрмия: 7\n",
            "Хиперион": "Доход крон: 7\nДоход сырья: 7\nАрмия: 10\n",
            "Халидон": "Доход крон: 4\nДоход сырья: 10\nАрмия: 6\n",
            "Этерия": "Доход крон: 6\nДоход сырья: 8\nАрмия: 8\n"
        }
        return info.get(kingdom, "")

    def start_game(self, instance):
        # Очистка старых данных из БД
        conn = sqlite3.connect(db_path)
        clear_tables(conn)
        conn.close()

        # Восстановление из backup
        restore_from_backup()

        app = App.get_running_app()
        selected_kingdom = app.selected_kingdom

        if not selected_kingdom:
            print("Фракция не выбрана. Пожалуйста, выберите фракцию перед началом игры.")
            return

        # Загружаем данные из базы данных
        cities = load_cities_from_db(selected_kingdom)
        if not cities:
            print("Для выбранного княжества не найдено городов.")
            return

        # Передаем выбранное княжество на новый экран игры
        game_screen = GameScreen(selected_kingdom, cities, db_path=db_path)
        app.root.clear_widgets()

        # Создаем MapWidget с правильными параметрами
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
            if hasattr(child, 'game_process'):
                child.game_process.close_connection()
            if hasattr(child, 'results_game'):
                child.results_game.close_connection()

if __name__ == '__main__':
    EmpireApp().run()  # Запуск приложения
