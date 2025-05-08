
import json
import random
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
import sqlite3
from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'

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
            self.generate_sequence_event("positive")
        elif karma_score < 0:
            print("Отрицательное событие sequences!")
            self.generate_sequence_event("negative")
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
        # Фильтруем события по коэффициенту kf
        if event_type == "positive":
            cursor.execute("""
                SELECT id, description, effects
                FROM events
                WHERE event_type = 'sequences' AND effects LIKE '%kf%' AND CAST(json_extract(effects, '$.kf') AS REAL) > 2
                ORDER BY RANDOM()
                LIMIT 1
            """)
        elif event_type == "negative":
            cursor.execute("""
                SELECT id, description, effects
                FROM events
                WHERE event_type = 'sequences' AND effects LIKE '%kf%' AND CAST(json_extract(effects, '$.kf') AS REAL) <= 2
                ORDER BY RANDOM()
                LIMIT 1
            """)
        else:
            print(f"Неизвестный тип события: {event_type}")
            return

        event = cursor.fetchone()
        if not event:
            print(f"Событие типа '{event_type}' не найдено.")
            return

        event_id, description, effects = event
        effects = json.loads(effects)

        # Определяем, является ли событие положительным
        is_positive = event_type == "positive"

        # Обрабатываем событие как пассивное
        self.handle_passive_event(description, effects, is_positive)

    def handle_passive_event(self, description, effects, is_positive=False):
        """
        Обрабатывает пассивное событие: применяет эффекты и отображает временную стройку.
        :param description: Описание события.
        :param effects: Словарь с эффектами события.
        :param is_positive: True, если событие положительное.
        """
        # Применяем эффекты
        if "resource" in effects and "kf" in effects:
            resource = effects["resource"]
            kf = effects["kf"]
            current_value = self.get_resource_amount(resource)
            change = int(current_value * (kf - 1))  # Рассчитываем изменение
            self.update_resource(resource, change)
            print(f"Событие последствия: {description}. {resource} изменился на {change}.")

        # Отображаем временную стройку
        self.show_temporary_build(description, is_positive)

    def show_event_active_popup(self, description, option_1, option_2, effects):
        """
        Отображение активного события в виде модального окна с выбором.
        """
        content = BoxLayout(orientation="vertical", padding=10, spacing=10)
        label = Label(text=description, font_size=16, size_hint_y=None, height=100)
        button_1 = Button(text=option_1, size_hint_y=None, height=50, background_color=(0.2, 0.6, 1, 1))
        button_2 = Button(text=option_2, size_hint_y=None, height=50, background_color=(1, 0.2, 0.2, 1))

        popup = Popup(
            title="Событие",
            content=content,
            size_hint=(0.8, 0.5),
            title_align="center",
            auto_dismiss=False  # Запрещаем закрытие окна без выбора
        )

        def on_button_1(instance):
            # Применяем эффекты для опции 1
            self.apply_effects_with_economic_module(effects["option_1"])
            # Обновляем карму (+2 очка)
            self.update_karma(self.player_faction, 2)
            popup.dismiss()

        def on_button_2(instance):
            # Применяем эффекты для опции 2
            self.apply_effects_with_economic_module(effects["option_2"])
            # Обновляем карму (-3 очка)
            self.update_karma(self.player_faction, -3)
            popup.dismiss()

        button_1.bind(on_press=on_button_1)
        button_2.bind(on_press=on_button_2)

        content.add_widget(label)
        content.add_widget(button_1)
        content.add_widget(button_2)
        popup.open()

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
        Применяет штраф игроку.
        :param faction: Название фракции.
        :param minor: True для небольшого штрафа, False для серьезного.
        """
        penalty_amount = -5000 if minor else -20000
        cursor = self.db_connection.cursor()
        cursor.execute("""
            UPDATE resources
            SET amount = amount + ?
            WHERE faction = ? AND resource_type = 'Кроны'
        """, (penalty_amount, faction))
        self.db_connection.commit()
        print(f"Фракции {faction} списано {-penalty_amount} Крон.")

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

    def show_temporary_build(self, description, is_positive):
        """
        Отображает временную стройку справа на экране с адаптивным размером и черной рамкой.
        :param description: Описание события.
        :param is_positive: True для положительных событий, False для негативных.
        """
        # Определяем цвет текста
        text_color = (0, 1, 1, 1) if is_positive else (1, 0.8, 0, 1)  # Бирюзовый или желтый

        # Создаем Label с адаптивным размером
        build_label = Label(
            text=description,
            font_size=16 if is_positive else 14,  # Размер шрифта
            size_hint=(0.7, None),  # Ширина 30% от ширины окна, высота автоматическая
            height=30,  # Фиксированная высота
            pos_hint={"right": 1, "top": 0.2},
            color=text_color,  # Цвет текста
            halign="center",  # Выравнивание текста по центру
            valign="middle",
        )

        # Добавляем черную рамку с помощью Canvas
        with build_label.canvas.before:
            Color(0, 0, 0, 1)  # Черный цвет
            build_label.rect = Rectangle(
                pos=build_label.pos,
                size=build_label.size
            )

        # Обновляем позицию и размер прямоугольника при изменении размеров Label
        def update_rect(instance, value):
            instance.rect.pos = instance.pos
            instance.rect.size = instance.size

        build_label.bind(pos=update_rect, size=update_rect)

        # Добавляем виджет на экран игры
        self.game_screen.add_widget(build_label)

        # Удаляем виджет через 5 секунд
        def remove_build(dt):
            self.game_screen.remove_widget(build_label)

        Clock.schedule_once(remove_build, 5)
