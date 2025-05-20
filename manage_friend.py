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

def has_pending_action():
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM last_click")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def get_city_faction(city_name):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT faction FROM cities WHERE name=?", (city_name,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def get_allies_for_faction(faction_name):
    conn = sqlite3.connect(db_path)
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
    conn.close()
    return allies


class ManageFriend(Popup):
    """
    Окно союзников с улучшенным дизайном
    """
    def __init__(self, faction_name, game_area, **kwargs):
        super().__init__(**kwargs)
        self.faction_name = faction_name
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
        self.status_label = Label(
            text="",
            size_hint_y=None,
            height=dp(30),
            **STYLE_LABEL_TEXT
        )
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
        city_faction = get_city_faction(city_name)
        allies = get_allies_for_faction(self.faction_name)
        if action == "defense":
            if city_faction == self.faction_name:
                self.save_query_defense_to_db(city_name)
                self.status_label.text = f"Запрос на защиту города {city_name} отправлен."
                self._show_fullscreen_message(f"Город для защиты выбран: {city_name}")
            else:
                self.status_label.text = "Нельзя защищать чужие города."
        elif action == "attack":
            if city_faction != self.faction_name and city_faction not in allies:
                self.save_query_attack_to_db(city_name)
                self.status_label.text = f"Запрос на атаку города {city_name} отправлен."
                self._show_fullscreen_message(f"Город для атаки выбран: {city_name}")
            else:
                self.status_label.text = "Нельзя атаковать дружественные города."
        self.progress_bar.opacity = 0

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

        # Прогресс-бар
        self.progress_bar = ProgressBar(
            max=100,
            size_hint_y=None,
            height=dp(20)
        )
        self.progress_bar.opacity = 0

        # Графика прогрессбара
        with self.progress_bar.canvas.before:
            Color(0.3, 0.3, 0.3, 1)
            self.progress_bg = RoundedRectangle(
                size=self.progress_bar.size,
                pos=self.progress_bar.pos,
                radius=[dp(5)] * 4
            )
            Color(0.2, 0.6, 0.8, 1)
            self.progress_rect = RoundedRectangle(
                size=(0, self.progress_bar.height),
                pos=self.progress_bar.pos,
                radius=[dp(5)] * 4
            )

        self.progress_bar.bind(
            pos=self.update_progress_graphics,
            size=self.update_progress_graphics,
            value=self.update_progress_graphics
        )

        # Статус бар
        status_content = BoxLayout(orientation='vertical', spacing=dp(5))
        status_content.add_widget(self.status_label)
        status_content.add_widget(self.progress_bar)

        status_box = BoxLayout(
            size_hint_y=None,
            height=dp(70)
        )
        status_box.add_widget(status_content)

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
        main_container.add_widget(status_box)  # ← фиксированная высота
        main_container.add_widget(button_box)  # ← фиксированная высота

        self.content = main_container

    def update_progress_graphics(self, *args):
        self.progress_bg.pos = self.progress_bar.pos
        self.progress_bg.size = self.progress_bar.size
        self.progress_rect.pos = self.progress_bar.pos
        self.progress_rect.size = (
            self.progress_bar.value_normalized * self.progress_bar.width,
            self.progress_bar.height
        )

        self.progress_rect.pos = self.progress_bar.pos

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
            on_press=lambda btn: self._on_resource_selected(ally_name, "Кроны")
        )
        main_container.add_widget(btn_crowns)

        btn_materials = self.create_action_button(
            icon='files/pict/friends/economic_materials.png',
            text='Сырьё',
            bg_color=(0.3, 0.7, 0.3, 1),
            on_press=lambda btn: self._on_resource_selected(ally_name, "Сырьё")
        )
        main_container.add_widget(btn_materials)

        btn_workers = self.create_action_button(
            icon='files/pict/friends/economic_workers.png',
            text='Рабочие',
            bg_color=(0.8, 0.6, 0.2, 1),
            on_press=lambda btn: self._on_resource_selected(ally_name, "Рабочие")
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
            on_press=lambda btn: self._on_action_wrapper('defense', ally_name, btn)
        )
        main_container.add_widget(btn_defense)

        btn_attack = self.create_action_button(
            icon='files/pict/friends/military_attack.png',
            text='Атака',
            bg_color=(0.8, 0.3, 0.3, 1),
            on_press=lambda btn: self._on_action_wrapper('attack', ally_name, btn)
        )
        main_container.add_widget(btn_attack)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(main_container)
        return scroll

    def create_action_button(self, icon, text, bg_color, on_press):
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
                on_press(btn_layout)
                return True
            return False

        btn_layout.on_touch_down = on_touch_down

        return btn_layout

    def _on_action_wrapper(self, action, ally, instance):
        self._on_action(action, ally)


    def _on_resource_selected(self, ally, resource):
        self._send_request(ally, resource)

    def _get_allies_from_db(self):
        conn = sqlite3.connect(db_path)
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
        conn.close()
        return list(allies)

    def _on_action(self, action, ally):
        """
        Обработчик нажатия на кнопки "Защита" или "Атака"
        """
        self.progress_bar.opacity = 1
        self.progress_bar.value = 0
        self.status_label.text = f"Ожидание выбора города для {'защиты' if action == 'defense' else 'атаки'}..."

        # Инициализация переменных для отслеживания выбора города
        self.city_wait_start_time = time.time()
        self.city_last_name = ""
        self.city_selection_duration = 2  # Минимальное время для подтверждения выбора

        # Запуск проверки выбора города
        self.city_check_event = Clock.schedule_interval(
            lambda dt: self._check_city_selection(dt, action, ally), 0.2
        )

        # Запуск прогресс-бара
        self.progress_event = Clock.schedule_interval(
            lambda dt: self._update_progress_bar(dt), 0.05
        )

        # Таймер на 10 секунд для отмены выбора
        self.cancel_timer = Clock.schedule_once(
            lambda dt: self._cancel_selection(action, ally), 5
        )

        self.dismiss()

    def _cancel_selection(self, action, ally):
        """
        Отменяет выбор города, если время истекло
        """
        # Останавливаем проверку выбора города
        if hasattr(self, 'city_check_event'):
            Clock.unschedule(self.city_check_event)
        if hasattr(self, 'progress_event'):
            Clock.unschedule(self.progress_event)

        # Сбрасываем интерфейс
        self.progress_bar.opacity = 0
        self.status_label.text = "Город не выбран. Выбор отменён."

        # Оповещаем пользователя
        self._show_fullscreen_message("Выбор города отменён")

    def _check_city_selection(self, dt, action, ally):
        """
        Проверяет, был ли выбран город
        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT city_name FROM last_click")
        row = cur.fetchone()
        conn.close()

        if row and row[0]:
            current_city = row[0]

            # Если город только что выбран
            if not self.city_last_name:
                self.city_last_name = current_city
                self.city_wait_start_time = time.time()

            # Если город выбран и прошло достаточно времени для подтверждения
            elif current_city == self.city_last_name:
                if time.time() - self.city_wait_start_time > self.city_selection_duration:
                    if self._has_existing_action():
                        self.status_label.text = "Нельзя отправить более одного запроса за ход."
                    else:
                        self._finalize_city_selection(current_city, action, ally)
                    Clock.unschedule(self.city_check_event)
                    Clock.unschedule(self.progress_event)
                    if hasattr(self, 'cancel_timer'):
                        Clock.unschedule(self.cancel_timer)
        else:
            # Если город не выбран и прошло 10 секунд
            if time.time() - self.city_wait_start_time > 10:
                self._cancel_selection(action, ally)
                Clock.unschedule(self.city_check_event)
                Clock.unschedule(self.progress_event)

    def _update_progress_bar(self, dt):
        if self.progress_bar.value < 100:
            self.progress_bar.value += 2
        else:
            self.progress_bar.value = 100

    def _has_existing_action(self):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM queries")
        count = cur.fetchone()[0]
        conn.close()
        return count > 0


    def save_query_attack_to_db(self, attack_city):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            ("", "", attack_city, self.faction_name)
        )
        conn.commit()
        conn.close()

    def save_query_defense_to_db(self, defense_city):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            ("", defense_city, "", self.faction_name)
        )
        conn.commit()
        conn.close()

    def save_query_resources_to_db(self, resource):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO queries (resource, defense_city, attack_city, faction) VALUES (?, ?, ?, ?)",
            (resource, "", "", self.faction_name)
        )
        conn.commit()
        conn.close()

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _send_request(self, ally, resource):
        self.save_query_resources_to_db(resource)
        self.status_label.text = f"Запрос на перевод {resource} нам {ally} отправлен."

    def open_popup(self):
        super().open()