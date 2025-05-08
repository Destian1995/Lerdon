import sqlite3

from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle


from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'

def merge_units(army):
    """
    Объединяет юниты одного типа в одну группу.
    :param army: Список юнитов (атакующих или обороняющихся).
    :return: Объединенный список юнитов.
    """
    merged_army = {}
    for unit in army:
        unit_name = unit['unit_name']
        if unit_name not in merged_army:
            merged_army[unit_name] = {
                "unit_name": unit['unit_name'],
                "unit_count": unit['unit_count'],
                "unit_image": unit.get('unit_image', ''),
                "units_stats": unit['units_stats']
            }
        else:
            merged_army[unit_name]['unit_count'] += unit['unit_count']
    return list(merged_army.values())

def update_results_table(db_connection, faction, units_combat, units_destroyed, enemy_losses):
    """
    Обновляет или создает запись в таблице results для указанной фракции.
    :param db_connection: Соединение с базой данных.
    :param faction: Название фракции.
    :param units_combat: Общее число юнитов фракции на начало боя.
    :param units_destroyed: Общие потери фракции после боя.
    :param enemy_losses: Потери противника (количество уничтоженных юнитов).
    """
    try:
        cursor = db_connection.cursor()
        db_connection.execute("BEGIN")

        # Проверяем, существует ли уже запись для этой фракции
        cursor.execute("SELECT COUNT(*) FROM results WHERE faction = ?", (faction,))
        exists = cursor.fetchone()[0]

        if exists > 0:
            # Обновляем существующую запись
            cursor.execute("""
                UPDATE results
                SET 
                    Units_Combat = Units_Combat + ?, 
                    Units_Destroyed = Units_Destroyed + ?,
                    Units_killed = Units_killed + ?
                WHERE faction = ?
            """, (units_combat, units_destroyed, enemy_losses, faction))
        else:
            # Вставляем новую запись
            cursor.execute("""
                INSERT INTO results (
                    Units_Combat, Units_Destroyed, Units_killed, 
                    Army_Efficiency_Ratio, Average_Deal_Ratio, 
                    Average_Net_Profit_Coins, Average_Net_Profit_Raw, 
                    Economic_Efficiency, faction
                )
                VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?)
            """, (units_combat, units_destroyed, enemy_losses, faction))

        db_connection.commit()
    except Exception as e:
        db_connection.rollback()
        print(f"Ошибка при обновлении таблицы results: {e}")

def calculate_experience(losing_side, db_connection):
    experience_points = {
        '1': 0.5,
        '2': 1.4,
        '3': 2.3,
        '4': 7.0
    }

    total_experience = 0

    for unit in losing_side:
        try:
            print(f"Обработка юнита: {unit.get('unit_name')}")
            print(f"Данные юнита: {unit}")

            if 'units_stats' not in unit or 'Класс юнита' not in unit['units_stats']:
                print(f"Проблема с данными юнита: {unit.get('unit_name')}")
                continue

            unit_class = unit['units_stats']['Класс юнита']
            killed_units = unit['killed_count']

            if killed_units > 0 and unit_class in experience_points:
                experience = experience_points[unit_class] * killed_units
                total_experience += experience
                print(f"Юнит: {unit['unit_name']}, Класс: {unit_class}, Убито: {killed_units}, Опыт: {experience}")
        except Exception as e:
            print(f"Ошибка при обработке юнита {unit.get('unit_name')}: {e}")

    if total_experience > 0:
        try:
            cursor = db_connection.cursor()
            db_connection.execute("BEGIN")

            # Проверяем, существует ли уже запись с id=1
            cursor.execute("SELECT COUNT(*) FROM experience WHERE id = 1")
            exists = cursor.fetchone()

            if exists['COUNT(*)'] > 0:
                # Обновляем существующее значение
                cursor.execute("""
                    UPDATE experience
                    SET experience_value = experience_value + ?
                    WHERE id = 1
                """, (total_experience,))
            else:
                # Вставляем новую запись
                cursor.execute("""
                    INSERT INTO experience (id, experience_value)
                    VALUES (1, ?)
                """, (total_experience,))

            db_connection.commit()
        except Exception as e:
            db_connection.rollback()
            print(f"Ошибка при обновлении таблицы experience: {e}")

def show_battle_report(report_data):
    """
    Отображает красивый отчет о бое с использованием возможностей Kivy.
    :param report_data: Данные отчета о бое.
    """
    # Основной контейнер
    content = BoxLayout(orientation='vertical', padding=10, spacing=10)

    # Фон с градиентом
    with content.canvas.before:
        Color(0.1, 0.1, 0.1, 1)  # Темный фон
        content.rect = Rectangle(size=content.size, pos=content.pos)
        content.bind(pos=lambda inst, value: setattr(inst.rect, 'pos', value),
                     size=lambda inst, value: setattr(inst.rect, 'size', value))

    # Создаем ScrollView для таблиц
    scroll_view = ScrollView()

    # Основной макет для таблиц
    main_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
    main_layout.bind(minimum_height=main_layout.setter('height'))

    # Функция для создания таблицы с данными
    def create_battle_table(side_data, title, side_color):
        table_layout = GridLayout(cols=4, size_hint_y=None, spacing=5, padding=5)
        table_layout.bind(minimum_height=table_layout.setter('height'))

        # Заголовок таблицы (добавляем только если title не пустой)
        if title:
            header_label = Label(
                text=f"[b][color={side_color}]{title}[/color][/b]",
                markup=True,
                size_hint_y=None,
                height=40,
                font_size=18,
                color=(1, 1, 1, 1)
            )
            main_layout.add_widget(header_label)

        # Заголовки столбцов
        headers = ["Тип Юнита", "На начало боя", "Потери", "Осталось юнитов"]
        for header in headers:
            label = Label(
                text=f"[b]{header}[/b]",
                markup=True,
                size_hint_y=None,
                height=30,
                color=(0.8, 0.8, 0.8, 1)
            )
            table_layout.add_widget(label)

        # Заполнение данных
        for unit_data in side_data:
            table_layout.add_widget(Label(text=unit_data['unit_name'], size_hint_y=None, height=30))
            table_layout.add_widget(Label(text=str(unit_data["initial_count"]), size_hint_y=None, height=30))
            table_layout.add_widget(Label(text=str(unit_data["losses"]), size_hint_y=None, height=30))
            table_layout.add_widget(Label(text=str(unit_data["final_count"]), size_hint_y=None, height=30))

        return table_layout

    # Разделение данных по сторонам
    attacking_data = [item for item in report_data if item['side'] == 'attacking']
    defending_data = [item for item in report_data if item['side'] == 'defending']

    # Цвета для сторон
    attacking_color = "#FF5733"  # Красный
    defending_color = "#33FF57"  # Зеленый

    # Определяем заголовки таблиц в зависимости от результата игрока
    # Определяем заголовки таблиц в зависимости от результата игрока
    attacking_title = None
    defending_title = None

    if attacking_data and attacking_data[0]['result']:
        # Определяем цвет заголовка на основе результата
        result_color = "#33FF57" if attacking_data[0]['result'] == "Победа" else "#FF5733"
        attacking_title = f"[color={result_color}]{attacking_data[0]['result']}[/color]"

    if defending_data and defending_data[0]['result']:
        # Определяем цвет заголовка на основе результата
        result_color = "#33FF57" if defending_data[0]['result'] == "Победа" else "#FF5733"
        defending_title = f"[color={result_color}]{defending_data[0]['result']}[/color]"

    # Создаем таблицы для атакующих и обороняющихся
    attacking_table = create_battle_table(attacking_data, attacking_title, attacking_color)
    defending_table = create_battle_table(defending_data, defending_title, defending_color)

    # Добавляем таблицы в основной макет
    main_layout.add_widget(attacking_table)
    main_layout.add_widget(defending_table)

    # Добавляем основной макет в ScrollView
    scroll_view.add_widget(main_layout)
    content.add_widget(scroll_view)

    # Вычисление общих потерь
    total_attacking_losses = sum(item['losses'] for item in attacking_data)
    total_defending_losses = sum(item['losses'] for item in defending_data)

    # Блок с итоговыми потерями
    totals_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=120, spacing=5)
    totals_label = Label(
        text="[b]Общие потери:[/b]",
        markup=True,
        size_hint_y=None,
        height=30,
        font_size=16,
        color=(1, 1, 1, 1)
    )
    totals_layout.add_widget(totals_label)

    totals_layout.add_widget(Label(
        text=f"Атакующая сторона: [color={attacking_color}]{total_attacking_losses}[/color]",
        markup=True,
        size_hint_y=None,
        height=30
    ))
    totals_layout.add_widget(Label(
        text=f"Обороняющаяся сторона: [color={defending_color}]{total_defending_losses}[/color]",
        markup=True,
        size_hint_y=None,
        height=30
    ))

    content.add_widget(totals_layout)

    # Кнопка закрытия окна
    close_button = Button(
        text="Закрыть",
        size_hint_y=None,
        height=50,
        background_color=(0.2, 0.6, 1, 1),  # Синий цвет
        color=(1, 1, 1, 1)
    )
    close_button.bind(on_release=lambda instance: popup.dismiss())
    content.add_widget(close_button)

    # Создаем всплывающее окно
    popup = Popup(
        title="Итоги боя",
        content=content,
        size_hint=(0.8, 0.8),
        background_color=(0.1, 0.1, 0.1, 1)  # Темный фон окна
    )
    popup.open()



def fight(attacking_city, defending_city, defending_army, attacking_army,
          attacking_fraction, defending_fraction, db_connection):
    """
    Основная функция боя между двумя армиями.
    """
    db_connection.row_factory = sqlite3.Row
    cursor = db_connection.cursor()
    try:
        cursor.execute("SELECT faction FROM user_faction")
        result = cursor.fetchone()
        user_faction = result['faction'] if result else None
    except Exception as e:
        print(f"Ошибка загрузки faction: {e}")
        user_faction = None
    is_user_involved = user_faction in (attacking_fraction, defending_fraction)

    # Объединяем одинаковые юниты
    merged_attacking = merge_units(attacking_army)
    # Объединяем гарнизон
    merged_defending = merge_units(defending_army)

    # Инициализируем счётчики для merged списков
    for u in merged_attacking + merged_defending:
        u['initial_count'] = u['unit_count']
        u['killed_count'] = 0

    # Приоритет для сортировки: класс (по возрастанию), затем атака (по убыванию)
    def priority(u):
        stats = u['units_stats']
        unit_class = int(stats.get('Класс юнита', 0))  # Класс юнита (чем меньше, тем раньше вступает в бой)
        attack = int(stats.get('Урон', 0))  # Урон (чем больше, тем раньше вступает в бой)
        return (unit_class, -attack)  # Сортируем по классу (возрастание), затем по урону (убывание)

    merged_attacking.sort(key=priority)
    merged_defending.sort(key=priority)

    # Бой: каждый атакующий против каждого обороняющего
    for atk in merged_attacking:
        for df in merged_defending:
            if atk['unit_count'] > 0 and df['unit_count'] > 0:
                atk_new, df_new = battle_units(atk, df, defending_city, user_faction)
                atk['unit_count'], df['unit_count'] = atk_new['unit_count'], df_new['unit_count']

    # Вычисляем потери после боя
    for u in merged_attacking + merged_defending:
        u['killed_count'] = u['initial_count'] - u['unit_count']

    # Определяем победителя
    winner = 'attacking' if any(u['unit_count'] > 0 for u in merged_attacking) else 'defending'

    # Обновляем гарнизоны
    update_garrisons_after_battle(
        winner=winner,
        attacking_city=attacking_city,
        defending_city=defending_city,
        attacking_army=merged_attacking,
        defending_army=merged_defending,
        attacking_fraction=attacking_fraction,
        cursor=db_connection.cursor()
    )

    # Подготовка данных для таблицы results
    total_attacking_units = sum(u['initial_count'] for u in merged_attacking)
    total_defending_units = sum(u['initial_count'] for u in merged_defending)
    total_attacking_losses = sum(u['killed_count'] for u in merged_attacking)
    total_defending_losses = sum(u['killed_count'] for u in merged_defending)

    # Обновляем таблицу results
    update_results_table(db_connection, attacking_fraction, total_attacking_units, total_attacking_losses, total_defending_losses)
    update_results_table(db_connection, defending_fraction, total_defending_units, total_defending_losses, total_attacking_losses)

    # Начисляем опыт игроку
    if is_user_involved:
        if winner == 'attacking' and attacking_fraction == user_faction:
            calculate_experience(merged_defending, db_connection)
        elif winner == 'defending' and defending_fraction == user_faction:
            calculate_experience(merged_attacking, db_connection)

    # Подготовка итоговых списков для отчёта
    final_report_attacking = []
    for u in merged_attacking:
        report_unit = {
            'unit_name': u['unit_name'],
            'initial_count': u['initial_count'],
            'unit_count': u['unit_count'],
            'killed_count': u['killed_count'],
        }
        final_report_attacking.append(report_unit)

    final_report_defending = []
    for u in merged_defending:
        report_unit = {
            'unit_name': u['unit_name'],
            'initial_count': u['initial_count'],
            'unit_count': u['unit_count'],
            'killed_count': u['killed_count'],
        }
        final_report_defending.append(report_unit)

    # Показываем единый отчёт при участии игрока
    if is_user_involved:
        report_data = generate_battle_report(
            final_report_attacking,
            final_report_defending,
            winner=winner,
            attacking_fraction=attacking_fraction,
            defending_fraction=defending_fraction,
            user_faction=user_faction
        )
        show_battle_report(report_data)

    return {
        "winner": winner,
        "attacking_fraction": attacking_fraction,
        "defending_fraction": defending_fraction,
        "attacking_losses": total_attacking_losses,
        "defending_losses": total_defending_losses,
        "attacking_units": final_report_attacking,
        "defending_units": final_report_defending
    }

def generate_battle_report(attacking_army, defending_army, winner, attacking_fraction, defending_fraction, user_faction):
    """
    Генерирует отчет о бое.
    :param attacking_army: Данные об атакующей армии (список словарей).
    :param defending_army: Данные об обороняющейся армии (список словарей).
    :param winner: Результат боя ('attacking' или 'defending').
    :param attacking_fraction: Название атакующей фракции.
    :param defending_fraction: Название обороняющейся фракции.
    :return: Отчет о бое (список словарей).
    """
    global attacking_result, defending_result
    report_data = []

    def process_army(army, side, result=None):
        for unit in army:
            initial_count = unit.get('initial_count', 0)
            final_count = unit['unit_count']
            losses = initial_count - final_count
            report_data.append({
                'unit_name': unit['unit_name'],
                'initial_count': initial_count,
                'final_count': final_count,
                'losses': losses,
                'side': side,
                'result': result  # Добавляем результат только если он указан
            })

    # Определяем результат только для фракции игрока
    if user_faction:
        if winner == 'attacking' and attacking_fraction == user_faction:
            attacking_result = "Победа"
            defending_result = None
        elif winner == 'defending' and defending_fraction == user_faction:
            attacking_result = None
            defending_result = "Победа"
        else:
            # Игрок проиграл
            if attacking_fraction == user_faction:
                attacking_result = "Поражение"
                defending_result = None
            elif defending_fraction == user_faction:
                attacking_result = None
                defending_result = "Поражение"
    else:
        # Если игрок не участвует, результаты не нужны
        attacking_result = None
        defending_result = None

    # Обработка армий
    process_army(attacking_army, 'attacking', attacking_result)
    process_army(defending_army, 'defending', defending_result)

    return report_data


def calculate_army_power(army):
    """
    Рассчитывает общую силу армии.
    :param army: Список юнитов в армии.
    :return: Общая сила армии (float).
    """
    total_power = 0
    for unit in army:
        unit_damage = unit['units_stats']['Урон']
        unit_count = unit['unit_count']
        total_power += unit_damage * unit_count
    return total_power


def calculate_unit_power(unit, is_attacking):
    """
    Рассчитывает силу одного юнита.
    :param unit: Данные о юните (словарь с характеристиками).
    :param is_attacking: True, если юнит атакующий; False, если защитный.
    :return: Сила юнита (float).
    """
    class_coefficients = {
        '1': 1.3,
        '2': 1.7,
        '3': 2.0,
        '4': 3.0
    }

    unit_class = unit['units_stats']['Класс юнита']
    coefficient = class_coefficients.get(unit_class, 1.0)

    if is_attacking:
        # Для атакующих юнитов
        attack = unit['units_stats']['Урон']
        return attack * coefficient
    else:
        # Для защитных юнитов
        durability = unit['units_stats']['Живучесть']
        defense = unit['units_stats']['Защита']
        return durability + defense

def battle_units(attacking_unit, defending_unit, city, user_faction):
    """
    Осуществляет бой между двумя юнитами.
    :param city:
    :param attacking_unit: Атакующий юнит.
    :param defending_unit: Защитный юнит.
    :return: Обновленные данные об атакующем и защитном юнитах после боя.
    """
    # Расчет силы атакующего юнита
    attack_points = calculate_unit_power(attacking_unit, is_attacking=True)
    total_attack_power = attack_points * attacking_unit['unit_count']

    # Расчет силы защитного юнита
    defense_points = calculate_unit_power(defending_unit, is_attacking=False)
    total_defense_power = defense_points * defending_unit['unit_count']

    damage_to_infrastructure(total_attack_power, city, user_faction)

    # Определение победителя раунда
    if total_attack_power > total_defense_power:
        # Атакующий побеждает
        remaining_power = total_attack_power - total_defense_power
        remaining_attackers = max(int(remaining_power / attack_points), 0)
        remaining_defenders = 0
    else:
        # Защитный побеждает
        remaining_power = total_defense_power - total_attack_power
        remaining_defenders = max(int(remaining_power / defense_points), 0)
        remaining_attackers = 0

    # Обновляем количество юнитов
    attacking_unit['unit_count'] = remaining_attackers
    defending_unit['unit_count'] = remaining_defenders

    return attacking_unit, defending_unit

def update_garrisons_after_battle(winner, attacking_city, defending_city,
                                  attacking_army, defending_army,
                                  attacking_fraction, cursor):
    """
    Обновляет гарнизоны после боя.
    """
    try:
        with cursor.connection:
            if winner == 'attacking':
                # Если победила атакующая сторона
                # Удаляем гарнизон обороняющейся стороны
                cursor.execute("""
                    DELETE FROM garrisons WHERE city_id = ?
                """, (defending_city,))

                # Перемещаем оставшиеся атакующие войска в захваченный город
                for unit in attacking_army:
                    if unit['unit_count'] > 0:
                        cursor.execute("""
                            INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(city_id, unit_name) DO UPDATE SET
                            unit_count = excluded.unit_count,
                            unit_image = excluded.unit_image
                        """, (
                            defending_city,
                            unit['unit_name'],
                            unit['unit_count'],
                            unit.get('unit_image', '')
                        ))

                # Обновляем принадлежность города
                cursor.execute("""
                    UPDATE city SET kingdom = ? WHERE fortress_name = ?
                """, (attacking_fraction, defending_city))
                cursor.execute("""
                    UPDATE cities SET faction = ? WHERE name = ?
                """, (attacking_fraction, defending_city))
                cursor.execute("""
                    UPDATE buildings
                    SET faction = ?
                    WHERE city_name = ?
                """, (attacking_fraction, defending_city))

            else:
                # Если победила обороняющаяся сторона
                # Сначала удаляем ВСЕ записи гарнизона обороняющегося города
                cursor.execute("DELETE FROM garrisons WHERE city_id = ?", (defending_city,))

                # Добавляем только оставшиеся юниты (unit_count > 0)
                for unit in defending_army:
                    if unit['unit_count'] > 0:
                        cursor.execute("""
                            INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(city_id, unit_name) DO UPDATE SET
                            unit_count = excluded.unit_count,
                            unit_image = excluded.unit_image
                        """, (
                            defending_city,
                            unit['unit_name'],
                            unit['unit_count'],
                            unit.get('unit_image', '')
                        ))

            # Обновляем гарнизон атакующего города (общий блок для обоих случаев)
            original_counts = {}
            cursor.execute("""
                SELECT unit_name, unit_count FROM garrisons WHERE city_id = ?
            """, (attacking_city,))
            for row in cursor.fetchall():
                original_counts[row['unit_name']] = row['unit_count']

            for unit in attacking_army:
                remaining_in_source = original_counts.get(unit['unit_name'], 0) - unit['initial_count']
                if remaining_in_source > 0:
                    cursor.execute("""
                        UPDATE garrisons 
                        SET unit_count = ? 
                        WHERE city_id = ? AND unit_name = ?
                    """, (remaining_in_source, attacking_city, unit['unit_name']))
                else:
                    cursor.execute("""
                        DELETE FROM garrisons 
                        WHERE city_id = ? AND unit_name = ?
                    """, (attacking_city, unit['unit_name']))

    except sqlite3.Error as e:
        print(f"Ошибка при обновлении гарнизонов: {e}")




#------------------------------------

def damage_to_infrastructure(all_damage, city_name, user_faction):
    """
    Вычисляет урон по инфраструктуре города и обновляет данные в базе данных.

    :param all_damage: Общий урон, который нужно нанести.
    :param city_name: Название города, по которому наносится урон.
    """
    global conn, damage_info

    # Константа для урона, необходимого для разрушения одного здания
    DAMAGE_PER_BUILDING = 45900

    # Подключение к базе данных
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Загрузка данных о зданиях для указанного города
        cursor.execute('''
            SELECT building_type, count 
            FROM buildings 
            WHERE city_name = ? AND count > 0
        ''', (city_name,))
        rows = cursor.fetchall()

        # Преобразование данных в словарь
        city_data = {}
        for row in rows:
            building_type, count = row
            city_data[building_type] = count

        if not city_data:
            return

        print(f"Данные инфраструктуры до удара: {city_data}")

        effective_weapon_damage = all_damage
        print(f"Эффективный урон по инфраструктуре: {effective_weapon_damage}")

        # Подсчет общего числа зданий
        total_buildings = sum(city_data.values())
        if total_buildings == 0:
            print("В городе нет зданий для нанесения урона.")
            return

        # Сколько зданий может быть разрушено этим уроном
        potential_destroyed_buildings = int(effective_weapon_damage // DAMAGE_PER_BUILDING)
        print(f"Максимально возможное количество разрушенных зданий: {potential_destroyed_buildings}")

        # Уничтожаем здания, начиная с больниц и фабрик
        damage_info = {}
        priority_buildings = ['Больница', 'Фабрика']  # Приоритетные типы зданий для уничтожения

        for building in priority_buildings:
            if building in city_data and city_data[building] > 0:
                count = city_data[building]
                if potential_destroyed_buildings >= count:
                    # Уничтожаем все здания этого типа
                    damage_info[building] = count
                    city_data[building] = 0
                    potential_destroyed_buildings -= count

                    # Обновляем данные в базе данных
                    cursor.execute('''
                        UPDATE buildings 
                        SET count = 0 
                        WHERE city_name = ? AND building_type = ?
                    ''', (city_name, building))
                else:
                    # Уничтожаем часть зданий
                    damage_info[building] = potential_destroyed_buildings
                    city_data[building] -= potential_destroyed_buildings

                    # Обновляем данные в базе данных
                    cursor.execute('''
                        UPDATE buildings 
                        SET count = count - ? 
                        WHERE city_name = ? AND building_type = ?
                    ''', (potential_destroyed_buildings, city_name, building))

                    potential_destroyed_buildings = 0

                if potential_destroyed_buildings == 0:
                    break

        print(f"Данные инфраструктуры после удара: {city_data}")

        # Сохраняем изменения в базе данных
        conn.commit()
        print('Обновленная инфраструктура сохранена.')

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
    finally:
        conn.close()

    if user_faction == 1:
        # Показать информацию об уроне
        show_damage_info_infrastructure(damage_info)


def show_damage_info_infrastructure(damage_info):
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.popup import Popup

    content = BoxLayout(orientation='vertical')
    message = "Информация об уроне по инфраструктуре:\n\n"
    for building, destroyed_count in damage_info.items():
        message += f"{building.capitalize()}, уничтожено зданий: {destroyed_count}\n"

    label = Label(text=message, size_hint_y=None, height=400)
    close_button = Button(text="Закрыть", size_hint_y=None, height=50)
    close_button.bind(on_release=lambda instance: popup.dismiss())

    content.add_widget(label)
    content.add_widget(close_button)

    popup = Popup(title="Результат удара по инфраструктуре", content=content, size_hint=(0.7, 0.7))
    popup.open()