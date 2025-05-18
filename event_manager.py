from lerdon_libraries import *

# === Настройка пути к базе данных ===
if platform == 'android':
    from android.storage import app_storage_path
    storage_dir = app_storage_path()
else:
    storage_dir = os.path.dirname(__file__)

original_db_path = os.path.join(os.path.dirname(__file__), 'game_data.db')
copied_db_path = os.path.join(storage_dir, 'game_data.db')

# Принудительно задаём глобальный db_path
db_path = copied_db_path  # ← Эта строка делает db_path доступным сразу

# Копируем БД, если её нет в пользовательской директории
if not os.path.exists(copied_db_path):
    if os.path.exists(original_db_path):
        import shutil
        shutil.copy(original_db_path, copied_db_path)
        print(f"✅ База данных скопирована в {copied_db_path}")
    else:
        raise FileNotFoundError(f"❌ game_data.db отсутствует в проекте!")


def get_adaptive_font_size(min_size=15, max_size=20):
    """Адаптирует размер шрифта под ширину экрана с учетом Android"""
    screen_width = Window.width

    # Увеличенный коэффициент для лучшей читаемости
    dynamic_size = min(max(screen_width * 1.8, min_size), max_size)

    # Учет масштабирования Android (если доступно)
    if platform == 'android':
        from jnius import autoclass
        context = autoclass('org.kivy.android.PythonActivity').mActivity
        resources = context.getResources()
        configuration = resources.getConfiguration()
        scaled_density = resources.getDisplayMetrics().scaledDensity
        dynamic_size = int(dynamic_size * scaled_density)

    return dynamic_size


class EventManager:
    def __init__(self, player_faction, game_screen, class_faction_economic):
        self.player_faction = player_faction
        self.game_screen = game_screen  # Ссылка на экран игры для отображения событий
        self.db = db_path
        self.db_connection = sqlite3.connect(self.db)  # Подключение к базе данных
        self.economics = class_faction_economic  # Экономический модуль

    def generate_event(self, current_turn):
        """
        Генерирует случайное событие из базы данных и определяет его тип.
        :param current_turn: Текущий ход игры.
        """
        # Проверяем карму и генерируем события sequences (если текущий ход >= 20)
        if current_turn >= 20:
            self.check_karma_and_generate_sequence(current_turn)

        # Генерируем обычное событие (active или passive)
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT id, description, event_type, effects, option_1_description, option_2_description
            FROM events
            WHERE event_type IN ('active', 'passive')
            ORDER BY RANDOM()
            LIMIT 1
        """)
        event = cursor.fetchone()
        if not event:
            print("События не найдены в базе данных.")
            return

        # Распаковываем данные события
        event_id, description, event_type, effects, option_1_description, option_2_description = event
        effects = json.loads(effects)  # Преобразуем JSON-строку в словарь

        # Добавляем описания опций в словарь effects
        effects["option_1_description"] = option_1_description
        effects["option_2_description"] = option_2_description

        # Обрабатываем событие в зависимости от его типа
        if event_type == "active":
            print(f"Активное событие: {description}")
            self.handle_active_event(description, effects)
        elif event_type == "passive":
            print(f"Пассивное событие: {description}")
            self.handle_passive_event(description, effects)

    def handle_active_event(self, description, effects):
        """
        Обрабатывает активное событие: отображает модальное окно с выбором.
        """
        print(f'-------------------------------------------- effects прилетело: {effects}')

        # Извлекаем текст опций из словаря effects или из базы данных
        option_1 = effects.get("option_1_description", "Не подгрузилось")
        option_2 = effects.get("option_2_description", "Не подгрузилось")

        self.show_event_active_popup(description, option_1, option_2, effects)


    def check_karma_and_generate_sequence(self, current_turn):
        """
        Проверяет карму и генерирует событие типа 'sequences' на основе значения karma_score.
        После проверки очищает значение кармы.
        :param current_turn: Текущий ход игры.
        """
        # Получаем текущее значение кармы и последний ход проверки
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT karma_score, last_check_turn FROM karma WHERE faction = ?", (self.player_faction,))
        result = cursor.fetchone()
        if not result:
            return

        karma_score, last_check_turn = result
        turns_since_last_check = current_turn - last_check_turn

        # Проверяем, прошло ли достаточно ходов для нового "среза"
        if turns_since_last_check < random.randint(8, 13):
            return

        # Генерируем событие на основе значения karma_score
        if karma_score > 6:
            print("Положительное событие sequences!")
            self.generate_sequence_event()
        elif karma_score < 0:
            print("Отрицательное событие sequences!")
            self.generate_sequence_event()
        else:
            print("Нейтральная карма. События sequences не генерируются.")

        # Очищаем значение кармы
        cursor.execute("""
            UPDATE karma
            SET karma_score = 0, last_check_turn = ?
            WHERE faction = ?
        """, (current_turn, self.player_faction))
        self.db_connection.commit()

        print(f"[DEBUG] Карма для фракции '{self.player_faction}' очищена.")

    def generate_sequence_event(self, event_type):
        """
        Генерирует событие типа 'sequences' из базы данных.
        :param event_type: Тип события ('positive' или 'negative').
        """
        cursor = self.db_connection.cursor()
        cursor.execute("""
            SELECT id, description
            FROM events
            WHERE event_type = 'sequences'
            ORDER BY RANDOM()
            LIMIT 1
        """)
        event = cursor.fetchone()
        if not event:
            print(f"Событие типа '{event_type}' не найдено.")
            return

        event_id, description = event
        # Показываем событие как модальное окно с кнопкой "Ясно"
        self.show_event_sequence_popup(description)

    def show_event_sequence_popup(self, description):
        """
        Отображает событие типа sequences в виде модального окна с кнопкой "Ясно".
        """
        font_size = get_adaptive_font_size()

        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))

        label = Label(
            text=description,
            font_size=font_size * 1.1,
            size_hint=(1, None),
            halign="center",
            valign="middle",
            markup=True,
            shorten=False,
            max_lines=0,
            line_height=1.2,
        )

        def update_label_size(instance, width):
            label.text_size = (width - dp(30), None)
            label.texture_update()
            if label.texture:
                label.height = max(dp(100), label.texture_size[1] + dp(10))

        content.bind(width=update_label_size)

        button_ok = self.create_gradient_button("Ясно", (0.2, 0.7, 0.2, 1), (0.1, 0.5, 0.1, 1), font_size)

        popup = self.create_styled_popup("", content)

        button_ok.bind(on_press=lambda x: popup.dismiss())

        content.add_widget(label)
        content.add_widget(button_ok)
        popup.open()

    def handle_passive_event(self, description, effects, event_type=None):
        """
        Обрабатывает пассивное событие: применяет эффекты (если они есть)
        и отображает бегущую строку для всех событий с event_type='passive' или 'sequences'.
        """
        # Применяем эффекты, если они есть
        if "resource" in effects and "kf" in effects:
            resource = effects["resource"]
            kf = effects["kf"]
            current_value = self.get_resource_amount(resource)
            change = int(current_value * kf)
            self.update_resource(resource, change)
            print(f"Событие {event_type}: {description}. {resource} изменен на {change}.")

        # Всегда отображаем бегущую строку
        self.show_temporary_build(description, event_type or "passive")

    def show_event_active_popup(self, description, option_1, option_2, effects):
        """
        Отображение активного события в виде модального окне с выбором.
        """
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        font_size = get_adaptive_font_size()

        # Адаптивный Label с текстом события и переносом слов
        label = Label(
            text=description,
            font_size=font_size*1.1,
            size_hint=(1, None),
            halign="center",
            valign="middle",
            markup=True,
            shorten=False,
            max_lines=0,
            line_height=1.2,
        )

        # Обновление размеров label при изменении ширины контента
        def update_label_size(instance, width):
            label.text_size = (width - dp(30), None)
            label.texture_update()
            if label.texture:
                label.height = max(dp(100), label.texture_size[1] + dp(10))

        content.bind(width=update_label_size)

        # Кнопки с фиксированной высотой и адаптивной шириной
        button_1 = self.create_gradient_button(option_1, (0.2, 0.6, 1, 1), (0.1, 0.4, 0.8, 1), font_size)
        button_2 = self.create_gradient_button(option_2, (1, 0.2, 0.2, 1), (0.8, 0.1, 0.1, 1), font_size)

        # Создаем стилизованное всплывающее окно
        popup = self.create_styled_popup("", content)
        popup.bind(on_open=lambda *args: update_label_size(content, content.width))

        # Обработчики нажатий
        def on_button_1(instance):
            self.apply_effects_with_economic_module(effects.get("option_1", {}))
            self.update_karma(self.player_faction, 2)
            popup.dismiss()

        def on_button_2(instance):
            self.apply_effects_with_economic_module(effects.get("option_2", {}))
            self.update_karma(self.player_faction, -3)
            popup.dismiss()

        button_1.bind(on_press=on_button_1)
        button_2.bind(on_press=on_button_2)

        content.add_widget(label)
        content.add_widget(button_1)
        content.add_widget(button_2)
        popup.open()

    def create_styled_popup(self, title, content):
        """Создает стилизованное всплывающее окно с анимацией и адаптивным размером"""
        width = min(Window.width * 0.95, dp(500))
        height = min(Window.height * 0.75, dp(600))

        popup = Popup(
            title=title,
            content=content,
            size_hint=(None, None),
            size=(width, height),
            auto_dismiss=False,
            title_align="center",
            separator_height=0
        )

        def update_rects(instance, value):
            instance.shadow.pos = (instance.x - dp(5), instance.y - dp(5))
            instance.shadow.size = (instance.width + dp(10), instance.height + dp(10))
            instance.bg.pos = (instance.x, instance.y)
            instance.bg.size = (instance.width, instance.height)

        with popup.canvas.before:
            Color(0.1, 0.1, 0.1, 0.3)
            popup.shadow = RoundedRectangle(radius=[dp(20)])
            Color(1, 1, 1, 1)
            popup.bg = RoundedRectangle(radius=[dp(15)])

        popup.bind(pos=update_rects, size=update_rects)
        update_rects(popup, None)

        popup.opacity = 0
        anim = Animation(opacity=1, duration=0.3)
        anim.start(popup)

        return popup

    def create_gradient_button(self, text, color1, color2, font_size):
        """Создает кнопку с градиентным фоном и закругленными углами без лишних прямоугольников"""
        btn = Button(
            text=text,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            font_size=font_size,
            size_hint=(1, None),
            height=dp(50),
            padding=(dp(10), dp(5)),
            markup=True,
            halign="center",
            valign="middle"
        )

        # Очищаем предыдущие графические инструкции
        btn.canvas.before.clear()

        with btn.canvas.before:
            Color(*color1)
            RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(10)])

        def update_graphics(instance, value):
            btn.canvas.before.clear()
            with btn.canvas.before:
                Color(*color1)
                RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(10)])

        btn.bind(pos=update_graphics, size=update_graphics)
        update_graphics(btn, None)

        return btn

    def check_karma_effects(self, faction, current_turn):
        """
        Проверяет карму и применяет бонусы/штрафы.
        :param faction: Название фракции.
        :param current_turn: Текущий ход.
        """
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT karma_score, last_check_turn FROM karma WHERE faction = ?", (faction,))
        result = cursor.fetchone()
        if not result:
            return

        karma_score, last_check_turn = result

        # Проверяем, прошло ли достаточно ходов для новой проверки
        if current_turn - last_check_turn < random.randint(14, 17):
            return

        # Применяем эффекты на основе кармы
        if karma_score > 5:
            print("Положительное событие! Бонус игроку.")
            self.apply_bonus(faction)
        elif 0 <= karma_score <= 5:
            print("Небольшой минус для игрока.")
            self.apply_penalty(faction, minor=True)
        else:
            print("Серьезные последствия!")
            self.apply_penalty(faction, minor=False)

        # Обновляем последний ход проверки
        cursor.execute("""
            UPDATE karma
            SET last_check_turn = ?
            WHERE faction = ?
        """, (current_turn, faction))
        self.db_connection.commit()

    def apply_bonus(self, faction):
        """
        Применяет положительный бонус игроку.
        :param faction: Название фракции.
        """
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE resources
            SET amount = amount + 10000
            WHERE faction = ? AND resource_type = 'Кроны'
        """, (faction,))
        self.db_connection.commit()
        print(f"Фракции {faction} начислено 10000 Крон.")

    def apply_penalty(self, faction, minor=True):
        """
        Применяет штраф игроку в процентах от текущих Крон.
        :param faction: Название фракции.
        :param minor: True для небольшого штрафа (10%), False для серьезного (30%).
        """
        # Получаем текущее количество Крон
        current_krons = self.get_resource_amount("Кроны")

        # Определяем процент штрафа
        penalty_percent = 0.10 if minor else 0.30  # 10% или 30%

        # Рассчитываем штраф
        penalty_amount = int(current_krons * penalty_percent)

        # Минимальный штраф - 100 Крон (если текущие ресурсы слишком малы)
        penalty_amount = max(penalty_amount, 100 if minor else 500)

        # Обновляем ресурсы в базе данных
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE resources
            SET amount = amount - ?
            WHERE faction = ? AND resource_type = 'Кроны'
        """, (penalty_amount, faction))
        self.db_connection.commit()

        # Логируем результат
        print(f"Фракции {faction} списано {penalty_amount} Крон ({penalty_percent * 100:.0f}% от текущих ресурсов).")

    def apply_effects_with_economic_module(self, effects):
        """
        Применение эффектов события через экономический модуль.
        """
        if "resource_changes" in effects:
            for resource, change_data in effects["resource_changes"].items():
                kf = change_data.get("kf", 1)
                current_value = self.get_resource_amount(resource)
                change = int(current_value * (kf - 1))  # Рассчитываем изменение
                print(f"[DEBUG] Изменение ресурса '{resource}': {change}")

                # Передаем изменения в экономический модуль
                self.economics.update_resource_now(resource, current_value + change)


    def get_resource_amount(self, resource_type):
        """Получение текущего значения ресурса."""
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT amount FROM resources WHERE faction = ? AND resource_type = ?", (self.player_faction, resource_type))
        result = cursor.fetchone()
        return result[0] if result else 0

    def update_resource(self, resource_type, change):
        """Обновление ресурсов."""
        cursor = self.db_connection.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO resources (faction, resource_type, amount)
            VALUES (?, ?, COALESCE((SELECT amount FROM resources WHERE faction = ? AND resource_type = ?), 0) + ?)
        """, (self.player_faction, resource_type, self.player_faction, resource_type, change))
        self.db_connection.commit()

    def update_karma(self, faction, karma_change):
        """
        Обновляет счетчик кармы для указанной фракции.
        :param faction: Название фракции.
        :param karma_change: Изменение кармы (+2 или -3).
        """
        cursor = self.db_connection.cursor()
        # Получаем текущее значение кармы
        cursor.execute("SELECT karma_score FROM karma WHERE faction = ?", (faction,))
        result = cursor.fetchone()
        current_karma = result[0] if result else 0

        # Обновляем значение кармы
        new_karma = current_karma + karma_change
        cursor.execute("""
            INSERT OR REPLACE INTO karma (id, faction, karma_score, last_check_turn)
            VALUES ((SELECT id FROM karma WHERE faction = ?), ?, ?, 
                    COALESCE((SELECT last_check_turn FROM karma WHERE faction = ?), 0))
        """, (faction, faction, new_karma, faction))
        self.db_connection.commit()

        print(f"[DEBUG] Карма для фракции '{faction}' обновлена: {new_karma}")

    def show_temporary_build(self, description, event_type):
        """
        Отображает бегущую строку слева с цветом в зависимости от типа события.
        :param description: Описание события.
        :param event_type: Тип события ('passive' или 'sequences').
        """
        # Определяем цвет текста и коэффициент скорости анимации
        if event_type == "passive":
            text_color = (1, 1, 1, 1)  # Белый
        elif event_type == "sequences":
            text_color = (0.5, 0.8, 1, 1)  # Светло-синий
        else:
            text_color = (1, 1, 1, 1)  # По умолчанию белый

        # Адаптивный размер шрифта
        font_size = get_adaptive_font_size(min_size=12, max_size=16)

        # Создаем Label с начальной позицией за пределами экрана слева
        build_label = Label(
            text=description,
            font_size=font_size,
            size_hint=(None, None),
            size=(Window.width * 0.7, dp(40)),  # Ширина 70% экрана
            pos=(-Window.width * 0.7, Window.height * 0.8),  # Начальная позиция за левой границей
            color=text_color,
            halign="left",
            valign="middle"
        )
        build_label.bind(texture_size=build_label.setter('size'))  # Автоматическая высота

        # Добавляем черную рамку
        with build_label.canvas.before:
            Color(0, 0, 0, 1)
            build_label.rect = Rectangle(pos=build_label.pos, size=build_label.size)

        # Обновление позиции прямоугольника при изменении Label
        def update_rect(instance, value):
            instance.rect.pos = instance.pos
            instance.rect.size = instance.size

        build_label.bind(pos=update_rect, size=update_rect)

        # Добавляем виджет на экран
        self.game_screen.add_widget(build_label)

        # Анимация бегущей строки
        move_distance = Window.width + build_label.width  # Расстояние до правой границы
        duration = move_distance / dp(100)  # Скорость анимации (100 px/сек)

        anim = Animation(pos=(-build_label.width, build_label.y), duration=duration)
        anim.start(build_label)

        # Удаление виджета после анимации
        def remove_widget(dt):
            self.game_screen.remove_widget(build_label)

        Clock.schedule_once(remove_widget, duration)
