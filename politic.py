from lerdon_libraries import *
from db_lerdon_connect import *


from economic import format_number
# Глобальная блокировка для работы с БД
db_lock = threading.Lock()
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
        text="МИД",
        size_hint=(1, None),
        height=50,
        font_size=sp(24),
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
        button.bind(on_release=lambda instance, cb=callback: cb(faction, game_area))
        button_layout.add_widget(button)

    # Кнопка "Вернуться"
    back_button = StyledButton(
        text="Вернуться",
        font_size=font_size * 1.2,
        button_color=(0.8, 0.2, 0.2, 1),  # Красный цвет
        text_color=default_text_color
    )
    back_button.bind(on_release=lambda x: modal.dismiss())

    # Добавляем всё в основное окно
    window.add_widget(title)
    scroll_view = ScrollView(size_hint=(1, 0.7))  # Добавляем ScrollView для кнопок
    scroll_view.add_widget(button_layout)
    window.add_widget(scroll_view)
    window.add_widget(back_button)

    modal.add_widget(window)
    modal.open()

# ======================Торговля
# Обновленная функция для создания формы торгового соглашения

def show_trade_agreement_form(faction, game_area):
    """Окно формы для торгового соглашения с полностью прозрачным фоном Popup."""
    font_size = dp(18)
    button_height = font_size * 3
    input_height = dp(44)
    padding = dp(16)
    spacing = dp(12)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    available_factions = all_factions(cursor)
    available_factions = [f for f in available_factions if f != faction]

    # --- ScrollView + GridLayout для формы ---
    scroll = ScrollView(size_hint=(1, 1))
    inner_layout = GridLayout(
        cols=1,
        spacing=spacing,
        padding=[padding, padding, padding, padding],
        size_hint_y=None
    )
    inner_layout.bind(minimum_height=inner_layout.setter('height'))

    # Заголовок
    title = Label(
        text="Торговое соглашение",
        size_hint_y=None,
        height=button_height,
        font_size=font_size * 1.4,
        bold=True,
        halign='center',
        valign='middle',
        color=[1, 1, 1, 1]
    )
    title.bind(size=lambda lbl, sz: lbl.setter('text_size')(lbl, (sz[0], None)))
    inner_layout.add_widget(title)

    # Spinner: "С какой фракцией?"
    factions_spinner = Spinner(
        text="С какой фракцией?",
        values=available_factions,
        size_hint_y=None,
        height=input_height,
        font_size=font_size,
        background_color=[0.20, 0.60, 0.86, 1],
        color=[1, 1, 1, 1],
        background_normal='',
        background_down='',
    )
    inner_layout.add_widget(factions_spinner)

    # Spinner: "Наш ресурс"
    our_resource_spinner = Spinner(
        text="Наш ресурс",
        values=["Рабочие", "Сырье", "Кроны"],
        size_hint_y=None,
        height=input_height,
        font_size=font_size,
        background_color=[0.20, 0.60, 0.86, 1],
        color=[1, 1, 1, 1],
        background_normal='',
        background_down='',
    )
    inner_layout.add_widget(our_resource_spinner)

    # Spinner: "Их ресурс"
    their_resource_spinner = Spinner(
        text="Их ресурс",
        values=["Рабочие", "Сырье", "Кроны"],
        size_hint_y=None,
        height=input_height,
        font_size=font_size,
        background_color=[0.20, 0.60, 0.86, 1],
        color=[1, 1, 1, 1],
        background_normal='',
        background_down='',
    )
    inner_layout.add_widget(their_resource_spinner)

    # Label + Slider: "Наш ресурс"
    our_slider_label = Label(
        text="Наш ресурс: 0",
        size_hint_y=None,
        height=input_height,
        font_size=font_size,
        halign='left',
        valign='middle',
        color=[1, 1, 1, 1]
    )
    our_slider_label.bind(size=lambda lbl, sz: lbl.setter('text_size')(lbl, (sz[0], None)))
    inner_layout.add_widget(our_slider_label)

    our_slider = Slider(
        min=0,
        max=100,
        value=0,
        step=1,
        size_hint_y=None,
        height=input_height
    )
    inner_layout.add_widget(our_slider)

    # Label для их ресурса
    their_slider_label = Label(
        text="Их ресурс: автоматический расчёт",
        size_hint_y=None,
        height=input_height,
        font_size=font_size,
        halign='left',
        valign='middle',
        color=[1, 1, 1, 1]
    )
    their_slider_label.bind(size=lambda lbl, sz: lbl.setter('text_size')(lbl, (sz[0], None)))
    inner_layout.add_widget(their_slider_label)

    # Многострочное поле для сводки (readonly)
    agreement_summary = TextInput(
        readonly=True,
        multiline=True,
        size_hint_y=None,
        height=button_height * 2,
        font_size=font_size,
        background_color=[0.10, 0.10, 0.10, 1],
        foreground_color=[1, 1, 1, 1]
    )
    inner_layout.add_widget(agreement_summary)

    scroll.add_widget(inner_layout)

    # -------------------------------------------------------------------
    # Функции для загрузки ресурсов, расчёта коэффициента и т.п.
    # -------------------------------------------------------------------
    def load_resources():
        cursor.execute("""
            SELECT resource_type, amount FROM resources 
            WHERE faction = ? AND resource_type IN ('Рабочие', 'Сырье', 'Кроны')
        """, (faction,))
        result = {res: 0 for res in ["Рабочие", "Сырье", "Кроны"]}
        for row in cursor.fetchall():
            result[row[0]] = int(row[1])
        return result

    def get_relation_level(f1, f2):
        cursor.execute("""
            SELECT relationship FROM relations 
            WHERE (faction1=? AND faction2=?) OR (faction1=? AND faction2=?)
        """, (f1, f2, f2, f1))
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def calculate_coefficient(rel):
        rel = int(rel)
        if rel < 15:
            return 0
        if 15 <= rel < 25:
            return 0.08
        if 25 <= rel < 35:
            return 0.3
        if 35 <= rel < 50:
            return 0.8
        if 50 <= rel < 60:
            return 1.0
        if 60 <= rel < 75:
            return 1.4
        if 75 <= rel < 90:
            return 2.0
        if 90 <= rel <= 100:
            return 2.9
        return 0

    def update_sliders(*args):
        res_type = our_resource_spinner.text
        if res_type == "Наш ресурс":
            return
        resources = load_resources()
        max_val = resources.get(res_type, 0)
        our_slider.max = max_val
        our_slider.value = 0
        our_slider_label.text = f"Наш ресурс: 0 / {format_number(max_val)}"
        their_slider_label.text = "Их ресурс: автоматический расчёт"
        agreement_summary.text = ""
        send_button.disabled = True

    def on_slider_change(instance, value):
        our_slider_label.text = f"Наш ресурс: {format_number(int(value))} / {format_number(int(our_slider.max))}"
        target = factions_spinner.text
        our_res = our_resource_spinner.text
        their_res = their_resource_spinner.text

        if target not in available_factions or our_res == "Наш ресурс" or their_res == "Их ресурс":
            agreement_summary.text = ""
            send_button.disabled = True
            return

        rel_lvl = get_relation_level(faction, target)
        coeff = calculate_coefficient(rel_lvl)
        if coeff == 0:
            their_slider_label.text = "Их ресурс: недоступен"
            agreement_summary.text = "Невозможно заключить соглашение — слишком низкие отношения."
            send_button.disabled = True
            return

        their_amount = int(value * coeff)
        their_slider_label.text = f"Их ресурс: {format_number(their_amount)}"

        agreement_summary.text = (
            f"Торговое соглашение с фракцией {target}.\n"
            f"Инициатор: {faction}.\n"
            f"Наш ресурс: {our_res} ({format_number(int(value))}).\n"
            f"Их ресурс: {their_res} ({format_number(their_amount)})."
        )
        send_button.disabled = False

    def check_existing_agreement(initiator, target):
        cursor.execute("""
            SELECT 1 FROM trade_agreements 
            WHERE (initiator=? AND target_faction=?)
               OR (initiator=? AND target_faction=?)
        """, (initiator, target, target, initiator))
        return cursor.fetchone() is not None

    def send_agreement(instance):
        target = factions_spinner.text
        our_res = our_resource_spinner.text
        their_res = their_resource_spinner.text
        our_amt = int(our_slider.value)
        their_amt = int(our_amt * calculate_coefficient(get_relation_level(faction, target)))

        if check_existing_agreement(faction, target):
            show_warning("Соглашение уже существует!")
            return

        try:
            conn2 = connect_to_db()
            cur2 = conn2.cursor()
            cur2.execute("""
                INSERT INTO trade_agreements 
                (initiator, target_faction, initiator_type_resource, 
                 target_type_resource, initiator_summ_resource, target_summ_resource)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (faction, target, our_res, their_res, our_amt, their_amt))
            conn2.commit()
            agreement_summary.text = (
                f"Условия договора отправлены фракции {target}.\n"
                f"Если его примут, поставки начнутся через 1 ход."
            )
            send_button.disabled = True
        except sqlite3.Error as e:
            show_warning(f"Ошибка базы данных: {e}")
        finally:
            conn2.close()

    # Привязка событий
    our_resource_spinner.bind(text=update_sliders)
    factions_spinner.bind(text=update_sliders)
    our_slider.bind(value=on_slider_change)

    # -------------------------------------------------------------------
    # Кнопки «Назад» и «Отправить» с StyledButton
    # -------------------------------------------------------------------
    buttons_box = BoxLayout(
        orientation='horizontal',
        size_hint_y=None,
        height=button_height + dp(4),
        spacing=spacing,
        padding=[padding, 0, padding, padding]
    )

    send_button = StyledButton(
        text="Отправить",
        font_size=font_size,
        button_color=[0.20, 0.60, 0.86, 1],
        text_color=[1, 1, 1, 1]
    )
    send_button.disabled = True
    send_button.bind(on_release=send_agreement)

    back_button = StyledButton(
        text="Назад",
        font_size=font_size,
        button_color=[0.90, 0.49, 0.13, 1],
        text_color=[1, 1, 1, 1]
    )
    back_button.bind(on_release=lambda _: popup.dismiss())

    buttons_box.add_widget(back_button)
    buttons_box.add_widget(send_button)

    # -------------------------------------------------------------------
    # Собираем main_layout и делаем фон прозрачным
    # -------------------------------------------------------------------
    main_layout = BoxLayout(
        orientation='vertical',
        spacing=spacing
    )

    # Рисуем тёмный фон за main_layout
    with main_layout.canvas.before:
        Color(0.12, 0.12, 0.12, 1)  # очень тёмно-серый/почти чёрный
        background_rect = Rectangle(pos=main_layout.pos, size=main_layout.size)

    def _update_bg_rect(instance, value):
        background_rect.pos = instance.pos
        background_rect.size = instance.size

    main_layout.bind(pos=_update_bg_rect, size=_update_bg_rect)

    main_layout.add_widget(scroll)
    main_layout.add_widget(buttons_box)

    popup = Popup(
        title="",
        content=main_layout,
        size_hint=(0.9, 0.9),
        auto_dismiss=False,
        separator_height=0,
        background='',                 # убираем стандартный фон Popup
        background_color=(0, 0, 0, 0)  # делаем фон полностью прозрачным
    )
    popup.open()


# Обработчик изменения размера окна
def on_window_resize(instance, width, height):
    """Обновляет интерфейс при изменении размера окна."""
    global font_size
    font_size = calculate_font_size()

def connect_to_db():
    """Подключение к базе данных."""
    return sqlite3.connect(db_path)


def show_cultural_exchange_form(faction, game_area, class_faction):
    """Окно формы для договора о культурном обмене (с StyledButton, увеличенным шрифтом, чуть меньшим размером окна и отступом перед кнопками)."""
    font_size = calculate_font_size()
    button_height = font_size * 3
    input_height = font_size * 2.5
    padding = font_size // 2
    spacing = font_size // 4

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Список всех фракций, кроме текущей
    available_factions = all_factions(cursor)
    available_factions = [f for f in available_factions if f != faction]

    # Создаём контент для Popup
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
        color=(1, 1, 1, 1),
        background_normal='',
        background_down='',
    )
    content.add_widget(factions_spinner)

    # Описание
    description_label = Label(
        text="Обмен культурными ценностями повышает доверие между фракциями (+7% к отношениям).\n"
             "Стоимость: от 25 млн. крон.",
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
        message_label.text = text
        message_label.color = color

    # Создаём экземпляр PoliticalCash
    political_cash = PoliticalCash(faction, class_faction)

    # Переподключаемся к БД, чтобы узнать количество городов у фракций
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("SELECT faction, COUNT(*) FROM cities GROUP BY faction")
    city_counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()

    # Функция отправки предложения
    def send_proposal(instance):
        target_faction = factions_spinner.text
        if target_faction == "С какой фракцией?":
            show_warning("Пожалуйста, выберите фракцию!")
            return

        conn2 = connect_to_db()
        cursor2 = conn2.cursor()
        try:
            # Получаем текущее отношение
            cursor2.execute(
                "SELECT relationship FROM relations WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)",
                (faction, target_faction, target_faction, faction)
            )
            relation_record = cursor2.fetchone()
            if not relation_record:
                show_warning(f"Отношения между {faction} и {target_faction} не определены!")
                return

            current_relationship = int(relation_record[0])
            if current_relationship >= 90:
                show_warning(
                    f"Текущие отношения с {target_faction}: {current_relationship}\n"
                    "Отношения уже находятся на высоком уровне.",
                    color=(1, 0.6, 0, 1)
                )
                return

            # Узнаём число городов у целевой фракции
            cursor2.execute("SELECT COUNT(*) FROM cities WHERE faction = ?", (target_faction,))
            target_city_count = cursor2.fetchone()[0]

            # Стоимость договора
            cost = 5_000_000 + (20_000_000 * target_city_count)

            # Баланс игрока
            current_balance = political_cash.resources["Кроны"]
            if current_balance < cost:
                show_warning(f"Недостаточно средств, требуется {format_number(cost)} крон.")
                return

            # Пытаемся списать
            if not political_cash.deduct_resources(cost):
                show_warning("Мы недавно уже подписали один договор! Попробуйте позже")
                return

            # Обновляем отношения
            new_relationship = min(100, current_relationship + 7)
            cursor2.execute(
                "UPDATE relations SET relationship = ? WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)",
                (new_relationship, faction, target_faction, target_faction, faction)
            )
            conn2.commit()

            show_warning(
                f"Отношения с {target_faction} улучшены до {new_relationship}\n"
                f"Списано {format_number(cost)} крон",
                color=(0, 1, 0, 1)
            )

        except Exception as e:
            show_warning(f"Произошла ошибка: {e}")
        finally:
            conn2.close()

    # -------------------------------------------------------------------
    # Добавляем отступ перед кнопочной панелью
    # -------------------------------------------------------------------
    content.add_widget(Widget(size_hint=(1, None), height=spacing * 2))

    # Заменяем стандартные Button на StyledButton
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    send_button = StyledButton(
        text="Отправить предложение",
        font_size=font_size * 1.2,                # чуть больше шрифт
        button_color=[0.20, 0.60, 0.86, 1],      # ярко-синий
        text_color=[1, 1, 1, 1]
    )
    send_button.bind(on_release=send_proposal)

    back_button = StyledButton(
        text="Назад",
        font_size=font_size * 1.2,
        button_color=[0.80, 0.20, 0.20, 1],      # красно-бордовый
        text_color=[1, 1, 1, 1]
    )
    back_button.bind(on_release=lambda _: popup.dismiss())

    button_layout.add_widget(send_button)
    button_layout.add_widget(back_button)

    content.add_widget(button_layout)

    # -------------------------------------------------------------------
    # Сделаем окно чуть меньшим по высоте, чтобы убрать пустое пространство сверху
    # -------------------------------------------------------------------
    popup = Popup(
        title="Культурный обмен",
        content=content,
        size_hint=(0.8, 0.6),   # Уменьшили высоту с 0.7 до 0.6
        auto_dismiss=False
    )
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
        4: 3.0,
        5: 4.0
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
    """Окно формы для предложения о заключении мира (с использованием StyledButton)."""
    # Рассчитываем базовый размер шрифта
    font_size = calculate_font_size()
    button_height = font_size * 3   # Высота кнопок внутри StyledButton
    input_height = font_size * 2.5
    padding = font_size // 2
    spacing = font_size // 4

    conn = connect_to_db()
    cursor = conn.cursor()

    try:
        # Получаем текущие "военные" отношения
        cursor.execute(
            "SELECT faction2, relationship FROM diplomacies WHERE faction1 = ?",
            (player_faction,)
        )
        relations = {f: status for f, status in cursor.fetchall()}

        # Берем все активные фракции и фильтруем только те, с кем в "войне"
        conn2 = sqlite3.connect(db_path)
        cursor2 = conn2.cursor()
        active_factions = all_factions(cursor2)
        available_factions = [f for f in active_factions if relations.get(f) == "война"]
        conn2.close()

        # Если нет фракций для мира
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
                color=(0, 1, 0, 1),  # Зеленый
                halign='center'
            )
            popup_content.add_widget(message_label)

            close_button = StyledButton(
                text="Закрыть",
                font_size=font_size * 1.2,
                button_color=[0.80, 0.20, 0.20, 1],  # Красный
                text_color=[1, 1, 1, 1]
            )
            close_button.bind(on_release=lambda _: popup.dismiss())
            popup_content.add_widget(close_button)

            popup = Popup(
                title="Заключение мира",
                content=popup_content,
                size_hint=(0.7, 0.3),
                auto_dismiss=False
            )
            popup.open()
            return

        # --- Основная форма ---
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
        title.bind(size=lambda lbl, sz: lbl.setter('text_size')(lbl, (sz[0], None)))
        content.add_widget(title)

        # Спиннер для выбора фракции
        factions_spinner = Spinner(
            text="С какой фракцией?",
            values=available_factions,
            size_hint=(1, None),
            height=input_height,
            font_size=font_size,
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            background_normal='',
            background_down=''
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
            message_label.text = text
            message_label.color = color

        # Функция для отправки предложения
        def send_proposal(instance):
            target_faction = factions_spinner.text
            if target_faction == "С какой фракцией?":
                show_warning("Пожалуйста, выберите фракцию!", color=(1, 0, 0, 1))
                return

            # Вычисляем очки армий
            player_points = calculate_peace_army_points(conn, player_faction)
            enemy_points = calculate_peace_army_points(conn, target_faction)

            if player_points == 0 and enemy_points > 0:
                show_warning("Обойдешься. Сейчас я отыграюсь по полной.", color=(1, 0, 0, 1))
                return

            # Если у противника нет армии
            if enemy_points == 0 and player_points >= enemy_points:
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
                show_warning(response, color=(0, 1, 0, 1))
                return

            # Если превосходство игрока
            if player_points > enemy_points:
                superiority_percentage = ((player_points - enemy_points) / max(enemy_points, 1)) * 100
                if superiority_percentage >= 70:
                    response = "Это что сейчас было?...Пора менять командование"
                elif 50 <= superiority_percentage < 70:
                    response = "Нихера себе повоевали...."
                elif 20 <= superiority_percentage < 50:
                    response = "Какой дебил нас сюда послал?.."
                elif 5 <= superiority_percentage < 20:
                    response = "Вам не стыдно слабых обижать?"
                else:
                    response = "В следующий раз мы будем лучше готовы"

                cursor.execute(
                    "UPDATE diplomacies SET relationship = ? WHERE faction1 = ? AND faction2 = ?",
                    ("нейтралитет", player_faction, target_faction)
                )
                cursor.execute(
                    "UPDATE diplomacies SET relationship = ? WHERE faction1 = ? AND faction2 = ?",
                    ("нейтралитет", target_faction, player_faction)
                )
                conn.commit()
                show_warning(response, color=(0, 1, 0, 1))

            # Если превосходство врага
            elif player_points < enemy_points:
                inferiority_percentage = ((enemy_points - player_points) / max(player_points, 1)) * 100
                if inferiority_percentage <= 15:
                    response = "Может Вы и правы, но мы еще готовы продолжать сопротивление..."
                    show_warning(response, color=(1, 1, 0, 1))
                else:
                    response = "Уже сдаетесь?! Мы еще не закончили Вас бить!"
                    show_warning(response, color=(1, 0, 0, 1))
            else:
                response = "Сейчас передохнем и в рыло дадим"
                show_warning(response, color=(1, 0, 0, 1))

        # --- Кнопочная панель ---
        button_layout = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=button_height,
            spacing=font_size // 2
        )

        send_button = StyledButton(
            text="Отправить предложение",
            font_size=font_size * 1.2,
            button_color=[0.20, 0.60, 0.86, 1],  # Синий
            text_color=[1, 1, 1, 1]
        )
        send_button.bind(on_release=send_proposal)

        back_button = StyledButton(
            text="Назад",
            font_size=font_size * 1.2,
            button_color=[0.90, 0.49, 0.13, 1],  # Оранжево-красный
            text_color=[1, 1, 1, 1]
        )
        back_button.bind(on_release=lambda _: popup.dismiss())

        button_layout.add_widget(send_button)
        button_layout.add_widget(back_button)

        content.add_widget(button_layout)

        # --- Собираем и показываем Popup ---
        popup = Popup(
            title="Заключение мира",
            content=content,
            size_hint=(0.7, 0.5),
            auto_dismiss=False
        )
        popup.open()

    except Exception as e:
        print(f"Ошибка при работе с дипломатией: {e}")


# Словарь фраз для каждой фракции
alliance_phrases = {
    "Селестия": "Мы Вас прикроем, от огня врагов!",
    "Аркадия": "Светлого неба!",
    "Этерия": "Вместе мы непобедимы!",
    "Халидон": "Надеюсь войны не будет...",
    "Хиперион": "Пора выбить кому то зубы. Так. На всякий случай"
}


def show_alliance_form(faction, game_area, class_faction):
    """Окно формы для предложения о создании альянса (обновлённый дизайн с StyledButton)."""
    font_size = calculate_font_size()
    button_height = font_size * 3
    input_height = font_size * 2.5
    padding = font_size // 2
    spacing = font_size // 4

    conn = sqlite3.connect(db_path)
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

    # Получаем текущие отношения
    cursor.execute("""
        SELECT faction1, faction2, relationship 
        FROM relations 
        WHERE faction1 = ? OR faction2 = ?
    """, (faction, faction))
    relations_data = {
        (row[1] if row[0] == faction else row[0]): row[2]
        for row in cursor.fetchall()
    }

    # Список всех фракций (исключая текущую)
    available_factions = all_factions(cursor)
    available_factions = [f for f in available_factions if f != faction]

    # Контент для Popup
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
    title.bind(size=lambda lbl, sz: lbl.setter('text_size')(lbl, (sz[0], None)))
    content.add_widget(title)

    # Спиннер для выбора фракции
    factions_spinner = Spinner(
        text="С какой фракцией?",
        values=available_factions,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        color=(1, 1, 1, 1),
        background_normal='',
        background_down=''
    )
    content.add_widget(factions_spinner)

    # Описание
    description_label = Label(
        text="Создание альянса возможно только при высоком уровне доверия (>90).\n"
             "Уровень отношений влияет на возможность заключения союза.",
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

    # Функция вывода предупреждений
    def show_warning(text, color=(1, 0, 0, 1)):
        message_label.text = text
        message_label.color = color

    # Функция отправки предложения
    def send_proposal(instance):
        target_faction = factions_spinner.text
        if target_faction == "С какой фракцией?":
            show_warning("Пожалуйста, выберите фракцию!")
            return

        # Уровень отношений
        relation_level = int(relations_data.get(target_faction, 0))

        # Проверка существующего союза
        cursor.execute("""
            SELECT COUNT(*) FROM diplomacies 
            WHERE (faction1 = ? OR faction2 = ?) AND relationship = 'союз'
        """, (faction, faction))
        if cursor.fetchone()[0] > 0:
            show_warning("У вашей фракции уже есть действующий союз!", color=(1, 0, 0, 1))
            return

        # Количество городов у целевой фракции
        cursor.execute("SELECT COUNT(*) FROM cities WHERE faction = ?", (target_faction,))
        target_city_count = cursor.fetchone()[0]

        # Стоимость альянса
        alliance_cost = 80_000_000 + (35_000_000 * target_city_count)

        # Баланс игрока
        political_cash = PoliticalCash(faction, class_faction)
        current_balance = political_cash.resources["Кроны"]
        if current_balance < alliance_cost:
            show_warning(
                f"Недостаточно средств для заключения альянса!\n"
                f"Требуется {format_number(alliance_cost)} крон.",
                color=(1, 0, 0, 1)
            )
            return

        # Проверяем уровень отношений
        if relation_level >= 90:
            if not political_cash.deduct_resources(alliance_cost):
                show_warning("Ошибка при списании средств!")
                return

            cursor.execute("""
                UPDATE diplomacies 
                SET relationship = 'союз' 
                WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
            """, (faction, target_faction, target_faction, faction))
            conn.commit()

            alliance_phrase = alliance_phrases.get(target_faction, "Союз заключён!")
            show_warning(
                f"{alliance_phrase}\n"
                f"Списано {format_number(alliance_cost)} крон",
                color=(0, 1, 0, 1)
            )
        elif 75 <= relation_level < 90:
            show_warning(
                "Друг. Мы должны сильнее доверять друг другу, тогда союз будет возможен.",
                color=(1, 0.6, 0, 1)
            )
        elif 50 <= relation_level < 75:
            show_warning(
                "Приятель. Пока сложно о чем-то конкретном говорить, давай лучше поближе узнаем друг друга.",
                color=(1, 0.6, 0, 1)
            )
        elif 30 <= relation_level < 50:
            show_warning(
                "Не сказал бы, что в данный момент нас интересуют подобные предложения.",
                color=(1, 0.6, 0, 1)
            )
        elif 15 <= relation_level < 30:
            show_warning(
                "Да я лучше башку в осиное гнездо засуну, чем вообще буду Вам отвечать.",
                color=(1, 0.6, 0, 1)
            )
        else:
            show_warning(
                "Вы там ещё не сдохли? Ну ничего, мы это исправим.",
                color=(1, 0, 0, 1)
            )

    # -------------------------------------------------------------------
    # Отступ перед кнопочной панелью
    # -------------------------------------------------------------------
    content.add_widget(Widget(size_hint=(1, None), height=spacing * 2))

    # Кнопочная панель с StyledButton
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    send_button = StyledButton(
        text="Отправить предложение",
        font_size=font_size * 1.2,
        button_color=[0.20, 0.60, 0.86, 1],  # Синий
        text_color=[1, 1, 1, 1]
    )
    send_button.bind(on_release=send_proposal)

    back_button = StyledButton(
        text="Назад",
        font_size=font_size * 1.2,
        button_color=[0.80, 0.20, 0.20, 1],  # Красно-бордовый
        text_color=[1, 1, 1, 1]
    )
    back_button.bind(on_release=lambda _: popup.dismiss())

    button_layout.add_widget(send_button)
    button_layout.add_widget(back_button)

    content.add_widget(button_layout)

    # -------------------------------------------------------------------
    # Уменьшаем высоту popup, чтобы убрать пустое пространство сверху
    # -------------------------------------------------------------------
    popup = Popup(
        title="Создание альянса",
        content=content,
        size_hint=(0.8, 0.6),  # Чуть меньше по высоте
        auto_dismiss=False
    )
    popup.open()

def show_declare_war_form(faction):
    """Окно формы для объявления войны (с обновлённым дизайном и StyledButton)."""
    font_size = calculate_font_size()
    button_height = font_size * 3
    input_height = font_size * 2.5
    padding = font_size // 2
    spacing = font_size // 4

    # Доступные цели соберём заранее
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Проверка текущего хода
            cursor.execute("SELECT turn_count FROM turn")
            turn_result = cursor.fetchone()
            if turn_result is None or turn_result[0] < 14:
                show_popup_message("Слишком рано", "Атаковать другие фракции можно только после 14 хода.")
                return

            # Получаем все активные фракции
            active_factions = all_factions(cursor)
            if faction not in active_factions:
                show_popup_message("Ошибка", f"Фракция '{faction}' не найдена среди активных фракций.")
                return

            # Текущие отношения
            cursor.execute("""
                SELECT faction1, faction2, relationship 
                FROM diplomacies 
                WHERE faction1 = ? OR faction2 = ?
            """, (faction, faction))
            relations = {}
            for row in cursor.fetchall():
                other = row[1] if row[0] == faction else row[0]
                relations[other] = row[2]

            # Фильтруем цели, где relationship != "война"
            available_targets = [
                other for other, status in relations.items()
                if status != "война" and other in active_factions
            ]
            if not available_targets:
                show_popup_message("Нет целей", "Нет доступных целей для объявления войны.")
                return

    except Exception as e:
        show_popup_message("Ошибка", f"Ошибка при работе с базой данных: {e}")
        return

    # Уникальные фразы для фракций
    faction_phrases = {
        "Селестия": "Вы нарываетесь на драку? Я к Вашим услугам!",
        "Аркадия": "Тебя давно по голове били? Сейчас исправим!",
        "Этерия": "Меня поражает Ваша самоуверенность...",
        "Халидон": "Пустыня поглодит Вас..",
        "Хиперион": "Я сейчас кому-то в лицо плюну...кто бы это мог быть?"
    }

    # Контент Popup
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
    title.bind(size=lambda lbl, sz: lbl.setter('text_size')(lbl, (sz[0], None)))
    content.add_widget(title)

    # Спиннер для выбора цели
    factions_spinner = Spinner(
        text="Выберите цель",
        values=available_targets,
        size_hint=(1, None),
        height=input_height,
        font_size=font_size,
        background_color=(0.2, 0.6, 1, 1),
        color=(1, 1, 1, 1),
        background_normal='',
        background_down=''
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

    def show_warning(text, color=(1, 0, 0, 1)):
        message_label.text = text
        message_label.color = color

    def declare_war(instance):
        target = factions_spinner.text
        if target == "Выберите цель":
            show_warning("Пожалуйста, выберите цель!")
            return

        try:
            with sqlite3.connect(db_path) as conn2:
                cursor2 = conn2.cursor()

                cursor2.execute("""
                    UPDATE diplomacies 
                    SET relationship = 'война' 
                    WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
                """, (faction, target, target, faction))

                cursor2.execute("""
                    UPDATE relations 
                    SET relationship = 0 
                    WHERE (faction1 = ? AND faction2 = ?) OR (faction1 = ? AND faction2 = ?)
                """, (faction, target, target, faction))

                conn2.commit()

            phrase = faction_phrases.get(target, f"Война объявлена против {target}!")
            show_warning(phrase, color=(1, 0, 0, 1))

        except Exception as e:
            show_popup_message("Ошибка", f"Ошибка при объявлении войны: {e}")

    # -------------------------------------------------------------------
    # Добавляем отступ перед кнопками
    # -------------------------------------------------------------------
    content.add_widget(Widget(size_hint=(1, None), height=spacing * 2))

    # Кнопочная панель с StyledButton
    button_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=button_height,
        spacing=font_size // 2
    )

    declare_button = StyledButton(
        text="Объявить войну",
        font_size=font_size * 1.2,
        button_color=[0.20, 0.60, 0.86, 1],  # Синий
        text_color=[1, 1, 1, 1]
    )
    declare_button.bind(on_release=declare_war)

    back_button = StyledButton(
        text="Назад",
        font_size=font_size * 1.2,
        button_color=[0.80, 0.20, 0.20, 1],  # Красно-бордовый
        text_color=[1, 1, 1, 1]
    )
    back_button.bind(on_release=lambda _: popup.dismiss())

    button_layout.add_widget(declare_button)
    button_layout.add_widget(back_button)
    content.add_widget(button_layout)

    # -------------------------------------------------------------------
    # Уменьшаем высоту popup, чтобы окно не было слишком высоким
    # -------------------------------------------------------------------
    popup = Popup(
        title="Объявление войны",
        content=content,
        size_hint=(0.8, 0.6),  # Компактнее по высоте
        auto_dismiss=False
    )
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
    close_button.bind(on_release=popup.dismiss)
    popup_content.add_widget(close_button)
    popup.open()




#-------------------------------------

def calculate_army_strength():
    """Рассчитывает силу армий для каждой фракции."""
    class_coefficients = {
        "1": 1.3,  # Класс 1: базовые юниты
        "2": 1.7,  # Класс 2: улучшенные юниты
        "3": 2.0,  # Класс 3: элитные юниты
        "4": 3.0,
        "5": 4.0
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
    """Создает таблицу рейтинга армий с улучшенным дизайном."""
    army_strength, formatted_army_strength = calculate_army_strength()
    if not army_strength:
        return GridLayout()

    max_strength = max(army_strength.values(), default=1)

    # Макет таблицы
    layout = GridLayout(
        cols=3,
        size_hint_y=None,
        spacing=dp(10),
        padding=[dp(10), dp(5), dp(10), dp(5)],
        row_default_height=dp(50),
        row_force_default=True
    )
    layout.bind(minimum_height=layout.setter('height'))

    # Цвета
    header_color = (0.1, 0.5, 0.9, 1)  # Темно-синий
    row_colors = [
        (1, 1, 1, 1),       # Белый
        (0.8, 0.9, 1, 1),   # Светло-голубой
        (0.6, 0.8, 1, 1),   # Голубой
        (0.4, 0.7, 1, 1),   # Сине-зеленый
        (0.2, 0.6, 1, 1)    # Темно-синий
    ]

    def create_label(text, color, halign="left", valign="middle", bold=False):
        lbl = Label(
            text=text,
            color=(0, 0, 0, 1),
            font_size=sp(14),
            size_hint_y=None,
            height=dp(50),
            halign=halign,
            valign=valign,
            bold=bold
        )
        lbl.bind(size=lbl.setter('text_size'))
        with lbl.canvas.before:
            Color(*color)
            lbl.rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(8)])
        lbl.bind(
            pos=lambda _, value: setattr(lbl.rect, 'pos', value),
            size=lambda _, value: setattr(lbl.rect, 'size', value)
        )
        return lbl

    # Заголовки
    layout.add_widget(create_label("Страна", header_color, halign="center", valign="middle", bold=True))
    layout.add_widget(create_label("Рейтинг", header_color, halign="center", valign="middle", bold=True))
    layout.add_widget(create_label("Мощь", header_color, halign="center", valign="middle", bold=True))

    sorted_factions = sorted(army_strength.items(), key=lambda x: x[1], reverse=True)

    for rank, (faction, strength) in enumerate(sorted_factions):
        rating = (strength / max_strength) * 100
        faction_name = faction_names.get(faction, faction)
        color = row_colors[rank % len(row_colors)]

        # Добавляем ячейки
        layout.add_widget(create_label(f"  {faction_name}", color, halign="left", valign="middle"))
        layout.add_widget(create_label(f"{rating:.1f}%", color, halign="center", valign="middle"))
        layout.add_widget(create_label(formatted_army_strength[faction], color, halign="right", valign="middle"))

    return layout

def show_ratings_popup():
    """Открывает всплывающее окно с рейтингом армий."""
    table_layout = create_army_rating_table()

    scroll_view = ScrollView(
        size_hint=(1, 1),
        bar_width=dp(6),
        scroll_type=['bars', 'content']
    )
    scroll_view.add_widget(table_layout)

    popup = Popup(
        title="Рейтинг армий",
        content=scroll_view,
        size_hint=(0.9, 0.8),
        pos_hint={'center_x': 0.5, 'center_y': 0.5},
        background_color=(0.1, 0.1, 0.1, 0.95),
        separator_color=(0.2, 0.6, 1, 1),
        title_color=(1, 1, 1, 1),
        title_size=sp(20)
    )
    popup.open()


#------------------------------------------------------------------
def start_politic_mode(faction, game_area, class_faction):
    """Инициализация политического режима для выбранной фракции"""

    from kivy.metrics import dp, sp
    from kivy.uix.widget import Widget

    is_android = platform == 'android'

    politics_layout = BoxLayout(
        orientation='horizontal',
        size_hint=(1, None),
        height=dp(70) if is_android else 60,
        pos_hint={'x': -0.15, 'y': 0},
        spacing=dp(10) if is_android else 10,
        padding=[dp(10), dp(5), dp(10), dp(5)] if is_android else [10, 5, 10, 5]
    )

    # Добавляем пустое пространство слева
    politics_layout.add_widget(Widget(size_hint_x=None, width=dp(20)))

    manage_friend_popup = ManageFriend(faction, game_area)

    def styled_btn(text, callback):
        btn = Button(
            text=text,
            size_hint_x=None,
            width=dp(120) if is_android else 100,
            size_hint_y=None,
            height=dp(60) if is_android else 50,
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size=sp(18) if is_android else 16,
            bold=True
        )

        with btn.canvas.before:
            Color(0.2, 0.6, 1, 1)
            btn.rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[15])

        def update_rect(instance, value):
            instance.rect.pos = instance.pos
            instance.rect.size = instance.size

        btn.bind(pos=update_rect, size=update_rect)
        btn.bind(on_release=callback)
        return btn

    btn_new = styled_btn("Дипломатия", lambda btn: show_new_agreement_window(faction, game_area, class_faction))
    btn_allies = styled_btn("Союзник", lambda btn: manage_friend_popup.open_popup())
    btn_army = styled_btn("Сила армий", lambda btn: show_ratings_popup())

    politics_layout.add_widget(btn_new)
    politics_layout.add_widget(btn_allies)
    politics_layout.add_widget(btn_army)

    # Опционально: добавить отступ справа
    # politics_layout.add_widget(Widget(size_hint_x=None, width=dp(20)))

    game_area.add_widget(politics_layout)