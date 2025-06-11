from lerdon_libraries import *
from db_lerdon_connect import *


STYLE_BUTTON = {
    'background_normal': '',
    'color': (1, 1, 1, 1),
    'size_hint_y': None,
    'height': dp(40),
}
STYLE_BUTTON_ACTION = {
    'background_normal': '',
    'color': (1, 1, 1, 1),
}
STYLE_BUTTON_DANGER = {
    'background_normal': '',
    'color': (1, 1, 1, 1),
}
STYLE_LABEL_HEADER = {
    'bold': True,
    'color': (0.9, 0.9, 0.9, 1),
    'font_size': dp(16),
}
STYLE_LABEL_TEXT = {
    'color': (0.8, 0.8, 0.8, 1),
}


class NonBlockingProgress(FloatLayout):
    def __init__(self, duration=6, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.duration = duration
        self.callback = callback
        self.remaining = duration
        self.opacity = 0.9
        self.size_hint = (0.7, None)
        self.height = dp(120)
        self.pos_hint = {'center_x': 0.5, 'top': 0.9}

        # Фон
        with self.canvas.before:
            Color(0, 0, 0, 0.8)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)] * 4)
            self.bind(pos=self._update_rect, size=self._update_rect)

        # Сообщение
        self.label = Label(
            text="Ожидание выбора города...",
            font_size=dp(18),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle',
            size_hint=(None, None),
            size=(self.width, dp(30)),
            pos_hint={'center_x': 0.5, 'top': 1}
        )
        self.label.bind(size=lambda instance, value: setattr(instance, 'text_size', value))

        # Прогресс бар
        self.progress_bar = ProgressBar(max=100, size_hint=(1, None), height=dp(20))
        with self.progress_bar.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            self.bg_rect = RoundedRectangle(
                size=self.progress_bar.size,
                pos=self.progress_bar.pos,
                radius=[dp(5)] * 4
            )
            Color(0.2, 0.6, 0.8, 1)
            self.fg_rect = RoundedRectangle(
                size=(0, self.progress_bar.height),
                pos=self.progress_bar.pos,
                radius=[dp(5)] * 4
            )
        self.progress_bar.bind(
            pos=self._update_progress_graphics,
            size=self._update_progress_graphics,
            value=self._update_progress_graphics
        )

        # Расположение виджетов внутри FloatLayout
        self.add_widget(self.label)
        self.add_widget(self.progress_bar)

        # Таймеры
        self.event = Clock.schedule_interval(self.update_progress, 0.05)
        self.timeout_event = Clock.schedule_once(self.on_timeout, self.duration)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _update_progress_graphics(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size
        progress_width = instance.width * (instance.value / instance.max)
        self.fg_rect.size = (progress_width, instance.height)
        self.fg_rect.pos = instance.pos

    def update_progress(self, dt):
        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0
        self.progress_bar.value = ((self.duration - self.remaining) / self.duration) * 100

    def on_timeout(self, *args):
        self.event.cancel()
        self.timeout_event.cancel()
        if self.callback:
            self.callback()





class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=self.background_color)
            self.rect = RoundedRectangle(
                size=self.size,
                pos=self.pos,
                radius=[dp(10)] * 4
            )
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class StyledDropDown(DropDown):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.auto_width = False
        self.width = dp(200)
        with self.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.bg = RoundedRectangle(
                size=self.size,
                pos=self.pos,
                radius=[dp(5)] * 4
            )
        self.bind(size=self._update_bg, pos=self._update_bg)

    def _update_bg(self, *args):
        self.bg.size = self.size
        self.bg.pos = self.pos

def get_city_faction(city_name, conn):
    cur = conn.cursor()
    cur.execute("SELECT faction FROM cities WHERE name=?", (city_name,))
    result = cur.fetchone()

    return result[0] if result else None


def get_allies_for_faction(faction_name, conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT faction1, faction2 FROM diplomacies "
        "WHERE (faction1=? OR faction2=?) AND relationship='союз'",
        (faction_name, faction_name)
    )
    allies = {
        row[1] if row[0] == faction_name else row[0]
        for row in cur.fetchall()
    }

    return allies


class ManageFriend(Popup):
    """
    Окно союзников с улучшенным дизайном
    """
    def __init__(self, faction_name, game_area, conn, **kwargs):
        super().__init__(**kwargs)
        self.game_area = game_area
        self.faction_name = faction_name
        self.conn = conn
        allies = self._get_allies_from_db()
        ally_name = allies[0] if allies else "Нет союзника"
        self.title = f"Союзник: {ally_name}"
        self.title_size = dp(18)
        self.title_color = (0.9, 0.9, 0.9, 1)
        self.separator_color = (0.3, 0.6, 0.8, 1)
        self.separator_height = dp(2)
        self.size_hint = (0.85, 0.85)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.background = 'atlas://data/images/defaulttheme/modalview-background'
        self.background_color = (0.1, 0.1, 0.15, 0.9)
        self.selection_mode = None
        self.selected_ally = None
        self.highlighted_city = None
        self._build_content()

    def _show_fullscreen_message(self, message):
        """
        Отображает всплывающее сообщение на весь экран
        """
        popup = ModalView(
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0.8),  # Полупрозрачный фон
            auto_dismiss=True  # Автоматически закрывается при клике
        )
        content = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            spacing=dp(10)
        )
        label = Label(
            text=message,
            font_size=dp(24),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        label.bind(size=label.setter('text_size'))  # Для корректного выравнивания текста
        close_button = StyledButton(
            text="Закрыть",
            background_color=(0.2, 0.6, 0.8, 1),
            size_hint_y=None,
            height=dp(50)
        )
        close_button.bind(on_release=popup.dismiss)
        content.add_widget(label)
        content.add_widget(close_button)
        popup.add_widget(content)
        popup.open()

    def _finalize_city_selection(self, city_name, action, ally):
        city_faction = get_city_faction(city_name, self.conn)
        allies = get_allies_for_faction(self.faction_name, self.conn)

        final_msg = ""
        if action == "defense":
            if city_faction == self.faction_name:
                self.save_query_defense_to_db(city_name)
                final_msg = f"Город для защиты выбран: {city_name}"
            else:
                final_msg = "Нельзя защищать чужие города."
        elif action == "attack":
            if city_faction != self.faction_name and city_faction not in allies:
                self.save_query_attack_to_db(city_name)
                final_msg = f"Город для атаки выбран: {city_name}"
            else:
                final_msg = "Нельзя атаковать дружественные города."

        self._show_fullscreen_message(final_msg)

    def _build_content(self):
        # Основной контейнер
        main_container = BoxLayout(
            orientation='vertical',
            spacing=dp(10),
            padding=dp(15)
        )

        # Фон основного контейнера
        with main_container.canvas.before:
            Color(0.15, 0.15, 0.2, 1)
            self.main_bg = RoundedRectangle(
                size=main_container.size,
                pos=main_container.pos,
                radius=[dp(10)] * 4
            )
            main_container.bind(
                pos=lambda *x: setattr(self.main_bg, 'pos', main_container.pos),
                size=lambda *x: setattr(self.main_bg, 'size', main_container.size)
            )

        # Таблица союзников (ScrollView должен растягиваться)
        table_scroll = self._create_table()
        table_scroll.size_hint_y = 1  # ← Теперь займёт всё доступное пространство

        # Кнопки управления
        button_box = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )

        close_btn = StyledButton(
            text="Закрыть",
            background_color=(0.2, 0.6, 0.8, 1),
            **STYLE_BUTTON
        )
        close_btn.bind(on_release=lambda btn: self.dismiss())
        button_box.add_widget(close_btn)

        # Добавляем всё в main_container
        main_container.add_widget(table_scroll)  # ← size_hint_y=1
        main_container.add_widget(button_box)  # ← фиксированная высота

        self.content = main_container

    def _create_table(self):
        allies = self._get_allies_from_db()

        main_container = BoxLayout(
            orientation='vertical',
            spacing=dp(15),
            padding=dp(20),
            size_hint_y=None
        )
        main_container.bind(minimum_height=main_container.setter('height'))
        main_container.minimum_height = dp(800)

        if not allies:
            no_allies_label = Label(
                text="У вас нет союзника",
                **STYLE_LABEL_HEADER,
                size_hint_y=None,
                height=dp(40)
            )
            main_container.add_widget(no_allies_label)
            scroll = ScrollView(size_hint=(1, 1))
            scroll.add_widget(main_container)
            return scroll

        ally_name = allies[0]
        # === Блок экономики ===
        economic_header = Label(
            text="Экономическая помощь",
            **STYLE_LABEL_HEADER,
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        economic_header.bind(size=economic_header.setter('text_size'))
        main_container.add_widget(economic_header)

        btn_crowns = self.create_action_button(
            icon='files/pict/friends/economic_crowns.png',
            text='Кроны',
            bg_color=(0.2, 0.6, 0.8, 1),
            on_release=lambda btn: self._on_resource_selected(ally_name, "Кроны")
        )
        main_container.add_widget(btn_crowns)

        btn_materials = self.create_action_button(
            icon='files/pict/friends/economic_materials.png',
            text='Сырьё',
            bg_color=(0.3, 0.7, 0.3, 1),
            on_release=lambda btn: self._on_resource_selected(ally_name, "Сырьё")
        )
        main_container.add_widget(btn_materials)

        btn_workers = self.create_action_button(
            icon='files/pict/friends/economic_workers.png',
            text='Рабочие',
            bg_color=(0.8, 0.6, 0.2, 1),
            on_release=lambda btn: self._on_resource_selected(ally_name, "Рабочие")
        )
        main_container.add_widget(btn_workers)

        # === Разделитель между блоками ===
        separator = Widget(size_hint_y=None, height=dp(10))
        main_container.add_widget(separator)

        # === Блок армии ===
        military_header = Label(
            text="Военная помощь",
            **STYLE_LABEL_HEADER,
            size_hint_y=None,
            height=dp(30),
            halign='left'
        )
        military_header.bind(size=military_header.setter('text_size'))
        main_container.add_widget(military_header)

        btn_defense = self.create_action_button(
            icon='files/pict/friends/military_defense.png',
            text='Защита',
            bg_color=(0.3, 0.7, 0.3, 1),
            on_release=lambda btn: self._on_action('defense', ally_name, btn)
        )
        main_container.add_widget(btn_defense)

        btn_attack = self.create_action_button(
            icon='files/pict/friends/military_attack.png',
            text='Атака',
            bg_color=(0.8, 0.3, 0.3, 1),
            on_release=lambda btn: self._on_action('attack', ally_name, btn)
        )
        main_container.add_widget(btn_attack)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(main_container)
        return scroll

    def create_action_button(self, icon, text, bg_color, on_release):
        btn_layout = BoxLayout(
            orientation='horizontal',
            spacing=dp(15),
            size_hint_y=None,
            height=dp(60)
        )

        with btn_layout.canvas.before:
            Color(rgba=bg_color)
            rect = RoundedRectangle(
                size=btn_layout.size,
                pos=btn_layout.pos,
                radius=[dp(10)] * 4
            )
            btn_layout.bind(pos=lambda *x: setattr(rect, 'pos', btn_layout.pos),
                            size=lambda *x: setattr(rect, 'size', btn_layout.size))

        img = Image(
            source=icon,
            size_hint=(None, None),
            width=dp(30),
            height=dp(30)
        )

        label = Label(
            text=text,
            color=(1, 1, 1, 1),
            font_size=dp(14),
            halign='left',
            valign='middle',
            size_hint_x=1
        )
        label.bind(size=label.setter('text_size'))

        btn_layout.add_widget(img)
        btn_layout.add_widget(label)

        def on_touch_down(touch):
            if btn_layout.collide_point(*touch.pos):
                on_release(btn_layout)
                return True
            return False

        btn_layout.on_touch_down = on_touch_down

        return btn_layout


    def _on_resource_selected(self, ally, resource):
        self._send_request(ally, resource)

    def _get_allies_from_db(self):
        conn = self.conn
        cur = conn.cursor()
        cur.execute(
            "SELECT faction1, faction2 FROM diplomacies "
            "WHERE (faction1=? OR faction2=?) AND relationship='союз'",
            (self.faction_name, self.faction_name)
        )
        allies = {
            r[1] if r[0] == self.faction_name else r[0]
            for r in cur.fetchall()
        }
        return list(allies)

    def _cancel_selection(self, action, ally):
        if hasattr(self, 'progress_bar'):
            self.progress_bar.progress_bar.value = 100

            def remove_progress(dt):
                if self.progress_bar and self.progress_bar in self.game_area.children:
                    self.game_area.remove_widget(self.progress_bar)

            Clock.schedule_once(remove_progress)

    def _on_action(self, action, ally, btn=None):
        self.dismiss()  # Закрываем окно союзника сразу

        # === Показываем неблокирующий прогресс-бар на game_area ===
        self.progress_bar = NonBlockingProgress(
            duration=6,
            callback=lambda: self._on_progress_timeout(action, ally)
        )
        self.game_area.add_widget(self.progress_bar)

        # === Инициализируем переменные выбора города ===
        self.city_last_name = None
        self.city_wait_start_time = time.time()
        self.city_selection_duration = 3
        self.action_mode = action
        self.selected_ally = ally
        self.total_selection_timeout = 5

        # === Проверка выбора города ===
        self.city_check_event = Clock.schedule_interval(
            lambda dt: self._check_city_selection(dt, action, ally), 0.2
        )

    def _on_progress_timeout(self, action, ally):
        self._cancel_selection(action, ally)

    def _check_city_selection(self, dt, action, ally):
        conn = self.conn
        cur = conn.cursor()
        cur.execute("SELECT city_name FROM last_click")
        row = cur.fetchone()
        current_city = row[0] if row and row[0] else None

        if current_city:
            if not hasattr(self, "city_last_name") or self.city_last_name != current_city:
                # Город изменился — перезапускаем таймер
                self.city_last_name = current_city
                self.city_wait_start_time = time.time()

                # === Настройка текста прогресс-бара ===
                self.progress_bar.label.text = f"Выбран: {current_city}..."
                self.progress_bar.label.font_size = dp(20)
                self.progress_bar.label.bold = True  # ← Жирный шрифт
                self.progress_bar.label.pos_hint = {'center_x': 0.5, 'top': 0.75}  # ← Ниже на экране

                # === Удаляем старую анимацию, если есть ===
                if hasattr(self, 'blink_animation'):
                    self.blink_animation.stop(self.progress_bar.label)

                # === Создаем новую плавную анимацию мигания ===
                self.blink_animation = Animation(opacity=0, duration=0.8, t='in_out_sine') + \
                                       Animation(opacity=1, duration=0.8, t='in_out_sine')
                self.blink_animation.repeat = True
                self.blink_animation.start(self.progress_bar.label)

            elapsed = time.time() - self.city_wait_start_time
            if elapsed >= self.city_selection_duration:
                self._finalize_city_selection(current_city, action, ally)
                Clock.unschedule(self.city_check_event)
                if hasattr(self, 'cancel_timer'):
                    Clock.unschedule(self.cancel_timer)
        else:
            elapsed = time.time() - self.city_wait_start_time
            if elapsed > self.total_selection_timeout:
                self._cancel_selection(action, ally)
                Clock.unschedule(self.city_check_event)

    def _blink_label(self, dt):
        if hasattr(self, 'progress_bar'):
            label = self.progress_bar.label
            label.opacity = 0 if label.opacity == 1 else 1

    def save_query_attack_to_db(self, attack_city):
        conn = self.conn
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            ("", "", attack_city, self.faction_name)
        )
        conn.commit()


    def save_query_defense_to_db(self, defense_city):
        conn = self.conn
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            ("", defense_city, "", self.faction_name)
        )
        conn.commit()


    def save_query_resources_to_db(self, resource):
        conn = self.conn
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            (resource, "", "", self.faction_name)
        )
        conn.commit()


    def _send_request(self, ally, resource):
        self.save_query_resources_to_db(resource)

    def open_popup(self):
        super().open()
