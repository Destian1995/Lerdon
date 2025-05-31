from lerdon_libraries import *
from db_lerdon_connect import *

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
        '3': 4.3,
        '4': 8.0,
        '5': 23.0,
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

def show_battle_report(report_data, is_user_involved=False, user_faction=None):
    """
    Отображает красивый отчет о бое с использованием возможностей Kivy.
    :param report_data: Данные отчета о бое.
    :param is_user_involved: Участвовал ли пользователь в бою.
    :param user_faction: Фракция пользователя (если участвовал).
    """
    if not report_data:
        print("Нет данных для отображения.")
        return

    # Основной контейнер
    content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))

    # Фон с градиентом
    with content.canvas.before:
        Color(0.1, 0.1, 0.1, 1)
        content.rect = Rectangle(size=content.size, pos=content.pos)
        content.bind(pos=lambda inst, value: setattr(inst.rect, 'pos', value),
                     size=lambda inst, value: setattr(inst.rect, 'size', value))

    # Основной макет для отчёта
    main_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
    main_layout.bind(minimum_height=main_layout.setter('height'))

    # === Единожды выводим название города ===
    city_label = Label(
        text=f"[b][color=#FFD700]Город: {report_data[0]['city']}[/color][/b]",
        markup=True,
        size_hint_y=None,
        height=dp(30),
        font_size=sp(16),
        color=(1, 1, 1, 1)
    )
    main_layout.add_widget(city_label)

    # === Выводим результат боя один раз ===
    result_text = ""
    result_color = "#FFFFFF"

    for item in report_data:
        if item.get("result"):
            result_text = item["result"]
            result_color = "#33FF57" if result_text == "Победа" else "#FF5733"
            break

    if result_text:
        result_label = Label(
            text=f"[b][color={result_color}]{result_text}[/color][/b]",
            markup=True,
            size_hint_y=None,
            height=dp(30),
            font_size=sp(16),
            color=(1, 1, 1, 1)
        )
        main_layout.add_widget(result_label)

    # Функция для создания таблицы
    def create_table(data, title):
        table_layout = GridLayout(
            cols=4,
            size_hint_y=None,
            spacing=dp(10),
            padding=dp(10)
        )
        table_layout.bind(minimum_height=table_layout.setter('height'))

        # Заголовок таблицы
        header = Label(
            text=f"[b]{title}[/b]",
            markup=True,
            size_hint_y=None,
            height=dp(40),
            font_size=sp(15),
            color=(1, 1, 1, 1)
        )
        main_layout.add_widget(header)

        # Заголовки столбцов
        headers = ["Тип Юнита", "На начало боя", "Потери", "Осталось юнитов"]
        for header_text in headers:
            label = Label(
                text=f"[b]{header_text}[/b]",
                markup=True,
                size_hint_y=None,
                height=dp(40),
                font_size=sp(14),
                color=(0.8, 0.8, 0.8, 1)
            )
            table_layout.add_widget(label)

        # Данные
        for unit_data in data:
            for value in [
                unit_data['unit_name'],
                str(unit_data['initial_count']),
                str(unit_data['losses']),
                str(unit_data['final_count'])
            ]:
                cell = Label(
                    text=value,
                    font_size=sp(14),
                    size_hint_y=None,
                    height=dp(40)
                )
                table_layout.add_widget(cell)

        main_layout.add_widget(table_layout)

    # Разделяем данные по сторонам
    attacking_data = [item for item in report_data if item['side'] == 'attacking']
    defending_data = [item for item in report_data if item['side'] == 'defending']

    create_table(attacking_data, "Атакующие силы")
    create_table(defending_data, "Оборонительные силы")

    # Кнопка закрытия окна
    close_button = Button(
        text="Закрыть",
        size_hint_y=None,
        height=dp(30 if platform == 'android' else 50),
        background_color=(0.2, 0.6, 1, 1),
        font_size=sp(16 if platform == 'android' else 16),
        color=(1, 1, 1, 1)
    )
    close_button.bind(on_release=lambda instance: popup.dismiss())

    # ScrollView
    scroll_view = ScrollView()
    scroll_view.add_widget(main_layout)

    content.add_widget(scroll_view)
    content.add_widget(close_button)

    # === Обновление досье только если игрок участвовал ===
    if is_user_involved and user_faction and report_data:
        is_victory = any(item['result'] == "Победа" for item in report_data)
        try:
            conn = sqlite3.connect(db_path)
            update_dossier_battle_stats(conn, user_faction, is_victory)
            conn.close()
        except Exception as e:
            print(f"[Ошибка] Не удалось обновить досье: {e}")

    # Всплывающее окно
    popup = Popup(
        title="Итоги боя",
        content=content,
        size_hint=(0.9, 0.85 if platform == 'android' else 0.8),
        background_color=(0.1, 0.1, 0.1, 1)
    )
    popup.open()

def fight(attacking_city, defending_city, defending_army, attacking_army,
          attacking_fraction, defending_fraction, db_connection):
    """
    Основная функция боя между двумя армиями.
    """
    print('Армия attacking_army: ', attacking_army)
    db_connection.row_factory = sqlite3.Row
    cursor = db_connection.cursor()
    try:
        cursor.execute("SELECT faction_name FROM user_faction")
        result = cursor.fetchone()
        user_faction = result['faction_name'] if result else None
    except Exception as e:
        print(f"Ошибка загрузки faction_name: {e}")
        user_faction = None
    is_user_involved = False

    if user_faction:
        cursor = db_connection.cursor()

        # Проверяем атакующую армию
        for unit in attacking_army:
            unit_name = unit['unit_name']
            try:
                cursor.execute("SELECT faction FROM units WHERE unit_name = ?", (unit_name,))
                result = cursor.fetchone()
                if result and result['faction'] == user_faction:
                    is_user_involved = True
                    break
            except Exception as e:
                print(f"Ошибка при проверке фракции для {unit_name}: {e}")

        # Если не найдено, проверяем обороняющуюся армию
        if not is_user_involved:
            for unit in defending_army:
                unit_name = unit['unit_name']
                try:
                    cursor.execute("SELECT faction FROM units WHERE unit_name = ?", (unit_name,))
                    result = cursor.fetchone()
                    if result and result['faction'] == user_faction:
                        is_user_involved = True
                        break
                except Exception as e:
                    print(f"Ошибка при проверке фракции для {unit_name}: {e}")

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
            user_faction=user_faction,
            city=defending_city
        )
        show_battle_report(report_data, is_user_involved=is_user_involved, user_faction=user_faction)

    return {
        "winner": winner,
        "attacking_fraction": attacking_fraction,
        "defending_fraction": defending_fraction,
        "attacking_losses": total_attacking_losses,
        "defending_losses": total_defending_losses,
        "attacking_units": final_report_attacking,
        "defending_units": final_report_defending
    }

def generate_battle_report(attacking_army, defending_army, winner, attacking_fraction, defending_fraction, user_faction, city):
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
    report_data = []  # ← Теперь это список, а не словарь

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
                'result': result,
                'city': city
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
        '4': 3.0,
        '5': 4.0
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

def update_dossier_battle_stats(db_connection, user_faction, is_victory):
    """
    Обновляет статистику по боям в таблице dossier для текущей фракции пользователя.

    :param db_connection: Соединение с базой данных.
    :param user_faction: Название фракции игрока.
    :param is_victory: True, если игрок победил, False — если проиграл.
    """
    try:
        cursor = db_connection.cursor()
        # Проверяем, существует ли запись для этой фракции
        cursor.execute("SELECT battle_victories, battle_defeats FROM dossier WHERE faction = ?", (user_faction,))
        result = cursor.fetchone()

        if result:
            # Если запись есть — обновляем нужное поле
            if is_victory:
                cursor.execute("""
                    UPDATE dossier
                    SET battle_victories = battle_victories + 1,
                        last_data = datetime('now')
                    WHERE faction = ?
                """, (user_faction,))
            else:
                cursor.execute("""
                    UPDATE dossier
                    SET battle_defeats = battle_defeats + 1,
                        last_data = datetime('now')
                    WHERE faction = ?
                """, (user_faction,))
        else:
            # Если записи нет — создаём новую
            if is_victory:
                cursor.execute("""
                    INSERT INTO dossier (
                        faction, battle_victories, battle_defeats, last_data
                    ) VALUES (?, 1, 0, datetime('now'))
                """, (user_faction,))
            else:
                cursor.execute("""
                    INSERT INTO dossier (
                        faction, battle_victories, battle_defeats, last_data
                    ) VALUES (?, 0, 1, datetime('now'))
                """, (user_faction,))
        db_connection.commit()
        print(f"[Досье] Обновлены данные для фракции '{user_faction}'")
    except Exception as e:
        db_connection.rollback()
        print(f"[Ошибка] Не удалось обновить досье: {e}")