from lerdon_libraries import *
from db_lerdon_connect import *

def format_number(number):
    """Форматирует число с добавлением приставок (тыс., млн., млрд., трлн., квадр., квинт., секст., септил., октил., нонил., децил., андец.)"""
    if not isinstance(number, (int, float)):
        return str(number)
    if number == 0:
        return "0"

    absolute = abs(number)
    sign = -1 if number < 0 else 1

    if absolute >= 1_000_000_000_000_000_000_000_000_000_000_000_000:  # 1e36
        return f"{sign * absolute / 1e36:.1f} андец."
    elif absolute >= 1_000_000_000_000_000_000_000_000_000_000_000:  # 1e33
        return f"{sign * absolute / 1e33:.1f} децил."
    elif absolute >= 1_000_000_000_000_000_000_000_000_000_000:  # 1e30
        return f"{sign * absolute / 1e30:.1f} нонил."
    elif absolute >= 1_000_000_000_000_000_000_000_000_000:  # 1e27
        return f"{sign * absolute / 1e27:.1f} октил."
    elif absolute >= 1_000_000_000_000_000_000_000_000:  # 1e24
        return f"{sign * absolute / 1e24:.1f} септил."
    elif absolute >= 1_000_000_000_000_000_000_000:  # 1e21
        return f"{sign * absolute / 1e21:.1f} секст."
    elif absolute >= 1_000_000_000_000_000_000:  # 1e18
        return f"{sign * absolute / 1e18:.1f} квинт."
    elif absolute >= 1_000_000_000_000_000:  # 1e15
        return f"{sign * absolute / 1e15:.1f} квадр."
    elif absolute >= 1_000_000_000_000:  # 1e12
        return f"{sign * absolute / 1e12:.1f} трлн."
    elif absolute >= 1_000_000_000:  # 1e9
        return f"{sign * absolute / 1e9:.1f} млрд."
    elif absolute >= 1_000_000:  # 1e6
        return f"{sign * absolute / 1e6:.1f} млн."
    elif absolute >= 1_000:  # 1e3
        return f"{sign * absolute / 1e3:.1f} тыс."
    else:
        return f"{number}"

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
    def __init__(self, player_faction, game_screen, class_faction_economic, conn):
        self.player_faction = player_faction
        self.game_screen = game_screen  # Ссылка на экран игры для отображения событий
        self.db_connection = conn # Используем единую сессию с БД
        self.economics = class_faction_economic  # Экономический модуль

    def generate_event(self, current_turn):
        """
        Генерирует случайное событие из базы данных и определяет его тип.
        За один ход происходит максимум одно событие.
        :param current_turn: Текущий ход игры.
        """
        # Проверяем карму и пытаемся сгенерировать событие sequences
        generated = self.check_karma_and_generate_sequence(current_turn)
        if generated:
            return  # Если событие sequences сгенерировано — выходим

        # Иначе генерируем обычное событие (active или passive)
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
        После успешной генерации события очищает значение кармы.
        """
        cursor = self.db_connection.cursor()
        cursor.execute("SELECT karma_score, last_check_turn FROM karma WHERE faction = ?", (self.player_faction,))
        result = cursor.fetchone()
        if not result:
            return False
        karma_score, last_check_turn = result

        turns_since_last_check = current_turn - last_check_turn

        # Проверяем, прошло ли достаточно ходов для нового "среза"
        if turns_since_last_check < random.randint(10, 15):  # ↑ увеличили интервал
            return False

        # Обновляем last_check_turn, чтобы избежать повторной попытки в ближайших ходах
        cursor.execute("""
            UPDATE karma
            SET last_check_turn = ?
            WHERE faction = ?
        """, (current_turn, self.player_faction))
        self.db_connection.commit()

        # Генерируем событие только если карма соответствует условиям
        if karma_score > 6:
            print("Положительное событие sequences!")
            success = self.generate_sequence_event('posi')
            if success:
                self.clear_karma(current_turn)
                return True
            return False
        elif karma_score < 0:
            print("Отрицательное событие sequences!")
            success = self.generate_sequence_event('negat')
            if success:
                self.clear_karma(current_turn)
                return True
            return False
        else:
            print("Нейтральная карма. События sequences не генерируются.")
        return False

    def clear_karma(self, current_turn):
        """
        Обнуляет значение кармы и обновляет last_check_turn.
        """
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE karma
            SET karma_score = 0, last_check_turn = ?
            WHERE faction = ?
        """, (current_turn, self.player_faction))
        self.db_connection.commit()
        print(f"[DEBUG] Карма для фракции '{self.player_faction}' очищена.")

    def generate_sequence_event(self, karma_type):
        """
        Генерирует событие sequences с учётом типа кармы.
        :param karma_type: 'posi' или 'negat'
        """
        kf_condition = "> 1.0" if karma_type == "posi" else "< 1.0"
        query = f"""
            SELECT id, description, effects 
            FROM events
            WHERE event_type = 'sequences'
              AND json_extract(effects, '$.kf') {kf_condition}
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor = self.db_connection.cursor()
        cursor.execute(query)
        event = cursor.fetchone()
        if not event:
            print(f"[WARN] Нет подходящих событий для '{karma_type}' (kf {kf_condition})")
            return False

        event_id, description, effects_json = event
        effects = json.loads(effects_json)

        # Получаем тип ресурса и коэффициент
        resource_type = effects.get("resource", None)
        kf = effects.get("kf", 1.0)

        if resource_type:
            current_value = self.get_resource_amount(resource_type)
            if kf > 1.0:
                # Увеличиваем ресурс по коэффициенту
                new_value = int(current_value * kf)
                self.economics.update_resource_now(resource_type, new_value)
                full_description = f"{description} [b]{resource_type}[/b] увеличено до {format_number(new_value)}."
            else:
                # Обнуляем ресурс, если kf <= 1.0
                self.economics.update_resource_now(resource_type, 0)
                full_description = f"{description} Мы потеряли: [b]{resource_type}[/b]"
        else:
            full_description = description

        # Отображаем как бегущую строку
        self.show_temporary_build(full_description, "sequences")
        return True

    def zero_resource(self, resource_type):
        """
        Обнуляет указанный ресурс через экономический модуль.
        """
        print(f"[DEBUG] Обнуление ресурса '{resource_type}' через экономический модуль.")
        self.economics.update_resource_now(resource_type, 0)  # ← Теперь через модуль

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
            self.update_karma(self.player_faction, 4)
            popup.dismiss()

        def on_button_2(instance):
            self.apply_effects_with_economic_module(effects.get("option_2", {}))
            self.update_karma(self.player_faction, -6)
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
        Отображает бегущую строку: появляется Label с черным фоном на всю ширину,
        по которому скользит текст события целиком, не обрезаясь.
        Label исчезает только после того, как текст полностью выйдет за левый край.
        """

        # Проверяем, есть ли уже активная бегущая строка
        if hasattr(self, '_running_marquee') and self._running_marquee:
            Clock.schedule_once(lambda dt: self.show_temporary_build(description, event_type), 1)
            return

        # === Цвет текста в зависимости от типа события ===
        if event_type == "passive":
            text_color = (1, 1, 1, 1)  # Белый
        elif event_type == "sequences":
            text_color = (0.5, 0.8, 1, 1)  # Светло-синий
        else:
            text_color = (1, 1, 1, 1)

        font_size = get_adaptive_font_size(min_size=14, max_size=20)

        # === Ширина контейнера — вся доступная область между панелью и правым краем экрана ===
        mode_panel_width = dp(90)  # ширина панели с кнопками режимов
        screen_width = Window.width
        label_height = dp(36)
        start_y = Window.height * 0.15  # ~15% от низа экрана

        # Создаем Label с полной длиной текста
        build_label = Label(
            text=description,
            font_size=font_size,
            color=text_color,
            halign="left",
            valign="middle",
            size_hint=(None, None),
            height=label_height,
            width=screen_width - mode_panel_width * 2,
            text_size=(None, label_height),
            shorten=False,
            markup=True
        )
        build_label.texture_update()
        text_width = build_label.texture_size[0] + dp(20)

        # === Контейнер для Label (начинается за правым краем экрана) ===
        container_width = screen_width - mode_panel_width * 2
        container = BoxLayout(
            orientation='horizontal',
            size_hint=(None, None),
            size=(text_width, label_height),
            pos=(screen_width, start_y)
        )

        # === Устанавливаем Label в контейнер и выравниваем по левому краю ===
        build_label.pos = (0, 0)
        build_label.size = (text_width, label_height)
        container.add_widget(build_label)

        # === Черный фон с прозрачностью вокруг контейнера ===
        with container.canvas.before:
            Color(0, 0, 0, 0.7)
            container.rect = Rectangle(pos=container.pos, size=container.size)

        def update_rect(instance, value):
            instance.rect.pos = instance.pos
            instance.rect.size = instance.size

        container.bind(pos=update_rect, size=update_rect)

        # Добавляем контейнер на экран
        self.game_screen.add_widget(container)

        # === Анимация движения текста внутри контейнера ===
        move_distance = text_width + container_width  # полное перемещение текста через контейнер
        duration = move_distance / dp(180)  # скорость движения (можно регулировать)

        # === Анимация всего контейнера ===
        anim_container = Animation(pos=(-text_width, start_y), duration=duration, t='linear')

        # === Привязка завершения анимации ===
        def on_animation_complete(*args):
            self.game_screen.remove_widget(container)
            self._running_marquee = False

        # Запуск анимации
        self._running_marquee = True
        anim_container.bind(on_complete=on_animation_complete)
        anim_container.start(container)
