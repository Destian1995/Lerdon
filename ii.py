import sqlite3
import random

from fight import fight
from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    import os
    db_path = os.path.join(app_storage_path(), 'game_data.db')
else:
    db_path = 'game_data.db'

class AIController:
    def __init__(self, faction, db_path=db_path):
        self.faction = faction
        self.turn = 0
        self.db_connection = sqlite3.connect(db_path)
        self.cursor = self.db_connection.cursor()
        self.garrison = self.load_garrison()
        self.relations = self.load_relations()
        self.previous_crowns = 0
        self.previous_raw = 0
        self.buildings = {}
        self.hospitals = 0
        self.factories = 0
        self.taxes = 0
        self.food_info = 0
        self.work_peoples = 0
        self.money_info = 0
        self.born_peoples = 0
        self.money_up = 0
        self.taxes_info = 0
        self.food_peoples = 0
        self.tax_effects = 0
        self.total_consumption = 0
        self.city_count = 0
        self.army = self.load_army()
        self.cities = self.load_cities()
        self.army_limit = self.calculate_army_limit()
        self.attacking_army = []
        self.average_deal_ratio = 0
        # Инициализация ресурсов по умолчанию
        self.money = 2000
        self.free_peoples = 0
        self.raw_material = 0
        self.population = 100
        self.resources = {
            'Кроны': self.money,
            'Рабочие': self.free_peoples,
            'Сырье': self.raw_material,
            'Население': self.population,
            'Текущее потребление': self.total_consumption,
            'Лимит армии': self.army_limit
        }

    # Методы загрузки данных из БД
    def load_resources(self):
        """
        Загружает текущие ресурсы фракции из таблицы resources.
        """
        try:
            self.cursor.execute('''
                SELECT resource_type, amount
                FROM resources
                WHERE faction = ?
            ''', (self.faction,))
            rows = self.cursor.fetchall()

            # Обновление ресурсов на основе данных из базы данных
            for resource_type, amount in rows:
                if resource_type == "Кроны":
                    self.money = amount
                elif resource_type == "Рабочие":
                    self.free_peoples = amount
                elif resource_type == "Сырье":
                    self.raw_material = amount
                elif resource_type == "Население":
                    self.population = amount

        except sqlite3.Error as e:
            print(f"Ошибка при загрузке ресурсов: {e}")

    def load_buildings(self):
        """
        Загружает данные о зданиях для текущей фракции из таблицы buildings.
        """
        try:
            self.cursor.execute('''
                SELECT city_name, building_type, count 
                FROM buildings 
                WHERE faction = ?
            ''', (self.faction,))
            rows = self.cursor.fetchall()

            # Сброс текущих данных о зданиях
            self.cities_buildings = {}
            total_hospitals = 0
            total_factories = 0

            for row in rows:
                city_name, building_type, count = row
                if city_name not in self.cities_buildings:
                    self.cities_buildings[city_name] = {"Больница": 0, "Фабрика": 0}

                # Обновление данных для конкретного города
                if building_type == "Больница":
                    self.cities_buildings[city_name]["Больница"] += count
                    total_hospitals += count
                elif building_type == "Фабрика":
                    self.cities_buildings[city_name]["Фабрика"] += count
                    total_factories += count

            # Обновление глобальных показателей
            self.hospitals = total_hospitals
            self.factories = total_factories

        except sqlite3.Error as e:
            print(f"Ошибка при загрузке зданий: {e}")

    def load_relations(self):
        """
        Загружает отношения текущей фракции с остальными из базы данных.
        Возвращает словарь, где ключи — названия фракций, а значения — уровни отношений.
        """
        try:
            # Выполняем запрос к таблице relations
            self.cursor.execute('''
                SELECT faction2, relationship
                FROM relations
                WHERE faction1 = ?
            ''', (self.faction,))
            rows = self.cursor.fetchall()

            # Преобразуем результат в словарь
            relations = {faction2: relationship for faction2, relationship in rows}
            return relations

        except sqlite3.Error as e:
            print(f"Ошибка при загрузке отношений: {e}")
            return {}

    def load_garrison(self):
        """
        Загружает гарнизон фракции из базы данных.
        Использует JOIN с таблицей units для фильтрации по faction.
        """
        try:
            # SQL-запрос с JOIN для получения гарнизона
            query = """
                SELECT g.city_id, g.unit_name, g.unit_count, u.faction
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE u.faction = ?
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()
            garrison = {}
            for row in rows:
                city_name, unit_name, count, faction = row
                if faction != self.faction:
                    continue  # Пропускаем юниты, не принадлежащие текущей фракции
                if city_name not in garrison:
                    garrison[city_name] = []
                garrison[city_name].append({
                    "unit_name": unit_name,
                    "unit_count": count
                })
            print(f"Гарнизон для фракции {self.faction} успешно загружен: {garrison}")
            return garrison
        except Exception as e:
            print(f"Ошибка при загрузке гарнизона для фракции {self.faction}: {e}")
            return {}

    def load_army(self):
        query = """
            SELECT unit_name, cost_money, cost_time, attack, defense, durability, unit_class, consumption 
            FROM units 
            WHERE faction = ?
        """
        self.cursor.execute(query, (self.faction,))
        return {
            row[0]: {  # unit_name
                "cost": {  # Стоимость юнита
                    "money": row[1],  # cost_money
                    "time": row[2]  # cost_time
                },
                "stats": {  # Характеристики юнита
                    "Атака": row[3],
                    "Защита": row[4],
                    "Прочность": row[5],
                    "Класс": row[6]
                },
                "consumption": row[7]
            } for row in self.cursor.fetchall()
        }

    def load_cities(self):
        """
        Загружает список городов для текущей фракции из таблицы cities.
        Выводит отладочную информацию о загруженных городах.
        Также подсчитывает количество городов и сохраняет его в self.city_count.
        """
        try:
            # SQL-запрос для получения списка городов
            query = """
                SELECT id, name 
                FROM cities 
                WHERE faction = ?
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            # Преобразуем результат в словарь {id: name}
            cities = {row[0]: row[1] for row in rows}

            # Подсчет количества городов
            self.city_count = len(cities)  # Сохраняем количество городов

            # Отладочный вывод: информация о загруженных городах
            print(f"Загружены города для фракции '{self.faction}':")
            if cities:
                for city_id, city_name in cities.items():
                    print(f"  ID: {city_id}, Название: {city_name}")
            else:
                print("  Города не найдены.")

            return cities
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке городов для фракции '{self.faction}': {e}")
            return {}

    # Методы сохранения данных в БД
    def save_resources_to_db(self):
        """
        Сохраняет текущие ресурсы фракции в таблицу resources.
        Обновляет только существующие записи, не добавляет новые.
        """
        try:
            for resource_type, amount in self.resources.items():
                # Проверяем, существует ли запись
                self.cursor.execute('''
                    SELECT amount
                    FROM resources
                    WHERE faction = ? AND resource_type = ?
                ''', (self.faction, resource_type))
                existing_record = self.cursor.fetchone()

                if existing_record:
                    # Обновляем существующую запись
                    self.cursor.execute('''
                        UPDATE resources
                        SET amount = ?
                        WHERE faction = ? AND resource_type = ?
                    ''', (amount, self.faction, resource_type))
                else:
                    # Если записи нет, пропускаем её (не добавляем новую)
                    pass

            # Сохраняем изменения в базе данных
            self.db_connection.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении ресурсов: {e}")

    def save_buildings(self):
        """
        Сохраняет данные о зданиях в базу данных.
        Удаляет старые записи для текущей фракции и добавляет новые.
        """
        try:
            # Удаляем старые записи для текущей фракции
            self.cursor.execute("DELETE FROM buildings WHERE faction = ?", (self.faction,))

            # Вставляем новые записи для каждого города и типа здания
            for city_name, data in self.buildings.items():
                for building_type, count in data["Здания"].items():
                    if count > 0:  # Сохраняем только те здания, количество которых больше 0
                        self.cursor.execute("""
                            INSERT INTO buildings (faction, city_name, building_type, count)
                            VALUES (?, ?, ?, ?)
                        """, (self.faction, city_name, building_type, count))

            # Сохраняем изменения в базе данных
            self.db_connection.commit()
            print("Данные о зданиях успешно сохранены в БД.")
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении данных о зданиях: {e}")

    def save_buildings_to_db(self):
        """
        Сохраняет текущие значения больниц и фабрик в базу данных.
        """
        try:
            # Удаляем старые записи для текущей фракции
            self.cursor.execute("""
                DELETE FROM buildings
                WHERE faction = ?
            """, (self.faction,))

            # Вставляем новые записи
            for city_name, data in self.buildings.items():
                hospital_count = data["Здания"]["Больница"]
                factory_count = data["Здания"]["Фабрика"]

                if hospital_count > 0:
                    self.cursor.execute("""
                        INSERT INTO buildings (faction, city_name, building_type, count)
                        VALUES (?, ?, ?, ?)
                    """, (self.faction, city_name, "Больница", hospital_count))

                if factory_count > 0:
                    self.cursor.execute("""
                        INSERT INTO buildings (faction, city_name, building_type, count)
                        VALUES (?, ?, ?, ?)
                    """, (self.faction, city_name, "Фабрика", factory_count))

            # Сохраняем изменения
            self.db_connection.commit()
            print("Данные о зданиях успешно сохранены в БД.")
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении данных о зданиях: {e}")

    def save_garrison(self):
        """
        Сохраняет гарнизон в базу данных.
        Обновляет существующие записи или создает новые, если их нет, ориентируясь на city_name и unit_name.
        """
        try:
            # Для каждого города обновляем или добавляем записи гарнизона
            for city_name, units in self.garrison.items():
                # Проверяем, принадлежит ли город текущей фракции
                self.cursor.execute("""
                    SELECT faction
                    FROM cities
                    WHERE name = ?
                """, (city_name,))
                result = self.cursor.fetchone()
                if not result or result[0] != self.faction:
                    print(f"Город {city_name} не принадлежит фракции {self.faction}. Пропускаем сохранение гарнизона.")
                    continue

                # Если город принадлежит фракции, сохраняем юниты
                for unit in units:
                    unit_name = unit['unit_name']
                    unit_count = unit['unit_count']
                    unit_image = self.get_unit_image(unit_name)
                    print(f"  Обработка юнита: {unit_name}, Количество: {unit_count}, Изображение: {unit_image}")
                    # Проверяем, существует ли уже запись для данного city_name и unit_name
                    self.cursor.execute("""
                        SELECT unit_count
                        FROM garrisons
                        WHERE city_id = ? AND unit_name = ?
                    """, (city_name, unit_name))
                    existing_record = self.cursor.fetchone()
                    if existing_record:
                        # Если запись существует, обновляем количество юнитов
                        new_count = existing_record[0] + unit_count
                        self.cursor.execute("""
                            UPDATE garrisons
                            SET unit_count = ?
                            WHERE city_id = ? AND unit_name = ?
                        """, (new_count, city_name, unit_name))
                    else:
                        # Если записи нет, добавляем новую
                        self.cursor.execute("""
                            INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                            VALUES (?, ?, ?, ?)
                        """, (city_name, unit_name, unit_count, unit_image))
            # Сохраняем изменения в базе данных
            self.db_connection.commit()
            print("Гарнизон успешно сохранен в БД.")
        except sqlite3.Error as e:
            print(f"Ошибка при сохранении гарнизона: {e}")

    def manage_buildings(self):
        try:
            crowns = self.resources['Кроны']

            # Бюджет на строительство (97% от текущих крон)
            building_budget = int(crowns * 0.97)

            # Проверяем, достаточно ли средств для начала строительства
            if building_budget < 350:
                print("Недостаточно средств для строительства.")
                return

            # Вычисляем, сколько зданий каждого типа можно построить
            result_buildings = building_budget // 350  # Количество пакетов по 350 крон
            hospitals_to_build = result_buildings - 1
            factories_to_build = result_buildings

            # Строим все больницы сразу
            if hospitals_to_build > 0:
                self.build_in_city('Больница', hospitals_to_build)

            # Строим все фабрики сразу
            if factories_to_build > 0:
                self.build_in_city('Фабрика', factories_to_build)

            # Сохраняем данные
            self.save_all_data()

        except Exception as e:
            print(f"Ошибка в manage_buildings: {e}")

    def build_in_city(self, building_type, count):
        """
        Строительство зданий в городе.
        :param building_type: Тип здания ("Больница" или "Фабрика").
        :param count: Максимальное количество зданий для постройки.
        """
        cost = 175 if building_type == 'Больница' else 175

        # Загружаем актуальные данные о городах фракции
        self.cities = self.load_cities()
        if not self.cities:
            print(f"Нет доступных городов для строительства у фракции '{self.faction}'.")
            return False

        import random
        target_city = random.choice(list(self.cities.values()))

        # Загружаем актуальные данные о зданиях в выбранном городе
        self.load_buildings()
        city_buildings = self.buildings.get(target_city, {"Здания": {"Больница": 0, "Фабрика": 0}})
        current_factories = city_buildings["Здания"].get("Фабрика", 0)
        current_hospitals = city_buildings["Здания"].get("Больница", 0)
        total_buildings = current_factories + current_hospitals

        # Максимальное количество зданий в городе
        max_buildings_per_city = 500

        # Вычисляем, сколько еще можно построить зданий в городе
        remaining_slots = max_buildings_per_city - total_buildings
        if remaining_slots <= 0:
            print(f"В городе {target_city} достигнут лимит зданий ({max_buildings_per_city}).")
            return False

        # Ограничиваем количество зданий, которое можно построить, минимальным значением
        # между запрошенным количеством (`count`) и доступными слотами (`remaining_slots`)
        count_to_build = min(count, remaining_slots)

        # Проверяем, достаточно ли денег для постройки
        total_cost = cost * count_to_build
        if self.resources['Кроны'] < total_cost:
            print(f"Недостаточно денег для постройки {count_to_build} зданий в городе {target_city}.")
            return False

        # Увеличиваем количество зданий в выбранном городе
        self.buildings.setdefault(target_city, {"Здания": {"Больница": 0, "Фабрика": 0}})
        self.buildings[target_city]["Здания"][building_type] += count_to_build

        # Обновляем глобальные переменные
        if building_type == 'Больница':
            self.hospitals += count_to_build
        elif building_type == 'Фабрика':
            self.factories += count_to_build

        # Списываем кроны
        self.resources['Кроны'] -= total_cost
        print(f"Построено {count_to_build} {building_type} в городе {target_city}")


        return True

    def sell_resources(self):
        if self.resources['Сырье'] > 10000:
            amount_to_sell = int(self.resources['Сырье'] * 0.95)
            earned_crowns = int(amount_to_sell * self.raw_material_price)
            self.resources['Сырье'] -= amount_to_sell
            self.resources['Кроны'] += earned_crowns

            # Рассчитываем эффективность сделки (цена за единицу сырья)
            price_per_lot = self.raw_material_price / 10000
            self.update_economic_efficiency(price_per_lot)  # Обновляем эффективность

            print(f"Продано {amount_to_sell} сырья за {earned_crowns} крон.")
            return True
        else:
            print("Недостаточно сырья для продажи.")
            return False

    def determine_dominant_unit_type(self):
        """Определяет доминирующий тип войск по максимальному потреблению"""
        try:
            # Получаем все юниты фракции с их характеристиками
            query = """
                SELECT g.unit_name, g.unit_count, u.attack, u.defense, u.consumption
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE u.faction = ?
            """
            self.cursor.execute(query, (self.faction,))
            units = self.cursor.fetchall()

            if not units:
                return 'attack'  # По умолчанию, если нет юнитов

            # Считаем общее потребление для каждого типа
            type_consumption = {'attack': 0, 'defense': 0}
            for unit in units:
                unit_name, count, attack, defense, consumption = unit
                total_consumption = count * consumption
                if defense > attack:
                    type_consumption['defense'] += total_consumption
                else:
                    type_consumption['attack'] += total_consumption

            # Определяем доминирующий тип
            return 'defense' if type_consumption['defense'] > type_consumption['attack'] else 'attack'

        except sqlite3.Error as e:
            print(f"Ошибка анализа войск: {e}")
            return 'attack'

    def hire_army(self):
        """
        Найм армии с учетом доминирующего типа войск в гарнизонах.
        """
        self.update_buildings_for_current_cities()

        # Текущие ресурсы
        crowns = self.resources['Кроны']
        works = self.resources['Рабочие']

        if crowns <= 0 or works <= 0:
            print("Недостаточно средств для найма армии.")
            return

        # Рассчитываем текущее потребление
        self.calculate_current_consumption()
        print(f"Текущее потребление: {self.total_consumption}, Лимит армии: {self.army_limit}")

        if self.total_consumption > self.army_limit:
            print("Текущее потребление достигло лимита. Наем армии невозможен.")
            return

        available_consumption = self.army_limit - self.total_consumption
        print(f"Доступное потребление: {available_consumption}")

        # Определяем доминирующий тип войск
        dominant_type = self.determine_dominant_unit_type()
        print(f"Доминирующий тип войск: {dominant_type}")

        # Устанавливаем приоритет найма противоположного типа
        resource_allocation = {
            "attack": 1.0 if dominant_type == 'defense' else 0.0,
            "defense": 1.0 if dominant_type == 'attack' else 0.0,
            "middle": 0.0,
            "hard_attack": 0.0
        }

        # Добавляем универсальные юниты в поздней игре
        if self.turn > 30:
            resource_allocation["middle"] = 0.1
            resource_allocation["hard_attack"] = 0.1

        # Списки для найма юнитов по категориям
        hired_units = {
            "attack": {"unit_name": None, "max_units": 0, "best_efficiency": 0},
            "defense": {"unit_name": None, "max_units": 0, "best_efficiency": 0},
            "middle": {"unit_name": None, "max_units": 0, "best_efficiency": 0},
            "hard_attack": {"unit_name": None, "max_units": 0, "best_efficiency": 0}
        }

        # Проходим по всем доступным юнитам
        for unit_name, unit_data in self.army.items():
            cost_money = unit_data['cost']['money']
            cost_time = unit_data['cost']['time']
            consumption = unit_data.get('consumption', 0)
            attack = unit_data['stats']['Атака']
            defense = unit_data['stats']['Защита']
            durability = unit_data['stats']['Прочность']

            # Пропускаем юниты, которые нельзя нанять
            if (affordable_units := min(crowns // cost_money, works // cost_time)) <= 0:
                continue

            # Учитываем лимит потребления
            max_units = min(affordable_units,
                            available_consumption // consumption if consumption > 0 else affordable_units)
            if max_units <= 0:
                continue

            # Определяем эффективность для каждой категории
            efficiency = {
                "attack": attack / (cost_money + cost_time),
                "defense": (defense + durability) / (cost_money + cost_time),
                "middle": (attack + defense + durability) / (cost_money + cost_time),
                "hard_attack": attack
            }

            # Обновляем лучшие юниты для каждой категории
            for category in ["attack", "defense", "middle", "hard_attack"]:
                if category == "hard_attack" and self.turn <= 30:
                    continue  # Супер-атакующие юниты только в поздней игре

                if efficiency[category] > hired_units[category]["best_efficiency"]:
                    hired_units[category].update({
                        "unit_name": unit_name,
                        "max_units": max_units,
                        "best_efficiency": efficiency[category]
                    })

        # Формируем итоговые юниты для найма
        total_units = {}
        for category, allocation in resource_allocation.items():
            if (unit_info := hired_units[category])["unit_name"] and allocation > 0:
                total_units[category] = {
                    "unit_name": unit_info["unit_name"],
                    "max_units": int(unit_info["max_units"] * allocation)
                }

        if not total_units:
            print("Недостаточно средств для найма армии.")
            return

        # Выбираем город с максимальным развитием
        target_city = max(
            self.buildings.items(),
            key=lambda x: sum(x[1]['Здания'].values()),
            default=(None, None)
        )[0]

        if not target_city:
            print("Нет доступных городов для найма.")
            return

        print(f"Выбран город для найма: {target_city}.")
        new_garrison = {target_city: []}

        for category, unit_info in total_units.items():
            unit_name = unit_info["unit_name"]
            max_units = unit_info["max_units"]
            unit_data = self.army[unit_name]
            consumption = unit_data['consumption']

            # Проверяем доступные ресурсы и потребление
            if crowns < (cost_money := unit_data['cost']['money'] * max_units) or \
                    works < (cost_time := unit_data['cost']['time'] * max_units) or \
                    available_consumption < (consumption * max_units):
                continue

            # Списываем ресурсы
            self.resources['Кроны'] -= cost_money
            self.resources['Рабочие'] -= cost_time
            available_consumption -= consumption * max_units

            # Добавляем в гарнизон
            new_garrison[target_city].append({
                "unit_name": unit_name,
                "unit_count": max_units
            })
            print(f"Нанято {max_units} юнитов '{unit_name}' в городе {target_city}.")

        # Обновляем гарнизон и сохраняем
        self.garrison.update(new_garrison)
        self.save_garrison()
        print("Гарнизон после найма:", self.garrison)

        # Перерасчет потребления
        self.calculate_and_deduct_consumption()
        print(f"После найма: Текущее потребление: {self.total_consumption}, Лимит: {self.army_limit}")

    def calculate_army_limit(self):
        """
        Рассчитывает максимальный лимит армии на основе базового значения и бонуса от городов.
        """
        base_limit = 400_000  # Базовый лимит 1 млн
        city_bonus = 100_000 * len(self.cities)  # Бонус за каждый город
        total_limit = base_limit + city_bonus
        return total_limit

    def calculate_current_consumption(self):
        """
        Рассчитывает текущее потребление армии.
        """
        try:
            self.total_consumption = 0  # Сбрасываем предыдущее значение

            # Выгрузка всех гарнизонов из таблицы garrisons
            self.cursor.execute("""
                SELECT city_id, unit_name, unit_count 
                FROM garrisons
            """)
            garrisons = self.cursor.fetchall()

            # Для каждого гарнизона находим соответствующий юнит в таблице units
            for garrison in garrisons:
                city_id, unit_name, unit_count = garrison

                # Получаем потребление юнита
                self.cursor.execute("""
                    SELECT consumption, faction 
                    FROM units 
                    WHERE unit_name = ?
                """, (unit_name,))
                unit_data = self.cursor.fetchone()

                if unit_data:
                    consumption, unit_faction = unit_data
                    if unit_faction == self.faction:
                        # Добавляем потребление данного типа юнита
                        self.total_consumption += consumption * unit_count

            print(f"Текущее потребление сырья: {self.total_consumption}")

        except Exception as e:
            print(f"Ошибка при расчете текущего потребления: {e}")

    def calculate_and_deduct_consumption(self):
        """
        Метод для расчета потребления сырья гарнизонами текущей фракции
        и вычета суммарного потребления из self.raw_material.
        """
        try:
            # Шаг 1: Выгрузка всех гарнизонов из таблицы garrisons
            self.cursor.execute("""
                SELECT city_id, unit_name, unit_count 
                FROM garrisons
            """)
            garrisons = self.cursor.fetchall()

            # Шаг 2: Для каждого гарнизона находим соответствующий юнит в таблице units
            for garrison in garrisons:
                city_id, unit_name, unit_count = garrison

                # Проверяем, к какой фракции принадлежит юнит
                self.cursor.execute("""
                    SELECT consumption, faction 
                    FROM units 
                    WHERE unit_name = ?
                """, (unit_name,))
                unit_data = self.cursor.fetchone()

                if unit_data:
                    consumption, faction = unit_data

                    # Учитываем только юниты текущей фракции
                    if faction == self.faction:
                        # Расчет потребления для данного типа юнита
                        self.total_consumption = consumption * unit_count

            # Шаг 3: Вычитание общего потребления из денег фракции
            self.raw_material -= self.total_consumption
            print(f"Общее потребление сырья: {self.total_consumption}")
            print(f"Остаток сырья у фракции: {self.raw_material}")

        except Exception as e:
            print(f"Произошла ошибка: {e}")

    def calculate_tax_income(self):
        """
        Рассчитывает налоговый доход на основе населения.
        """
        tax_rate = 0.34  # Базовая налоговая ставка (34%)
        return int(self.resources['Население'] * tax_rate)

    def update_buildings_from_db(self):
        """
        Загружает данные о количестве больниц и фабрик из базы данных.
        """
        try:
            query = """
                SELECT building_type, SUM(count)
                FROM buildings
                WHERE faction = ?
                GROUP BY building_type
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            # Обновляем количество зданий
            self.hospitals = next((count for b_type, count in rows if b_type == "Больница"), 0)
            self.factories = next((count for b_type, count in rows if b_type == "Фабрика"), 0)

            print(f"Загружены здания: Больницы={self.hospitals}, Фабрики={self.factories}")
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке данных о зданиях: {e}")

    def generate_raw_material_price(self):
        """
        Генерирует новую цену на сырье.
        """
        # Простая реализация: случайная цена в диапазоне
        self.raw_material_price = round(random.uniform(16200, 49250), 2200)
        print(f"Новая цена на сырье: {self.raw_material_price}")

    def update_trade_resources_from_db(self):
        """
        Обновляет ресурсы на основе торговых соглашений из базы данных.
        Учитывает текущую фракцию как инициатора или целевую фракцию.
        """
        try:
            # Убедитесь, что self.faction — это строка (или одиночное значение)
            if isinstance(self.faction, (list, tuple)):
                raise ValueError("self.faction должен быть строкой, а не коллекцией.")

            # Запрос для получения всех торговых соглашений, где текущая фракция участвует
            query = """
                SELECT initiator, target_faction, initiator_type_resource, target_type_resource,
                       initiator_summ_resource, target_summ_resource
                FROM trade_agreements
                WHERE target_faction = ?
            """
            # Передаем self.faction как одиночное значение
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            for row in rows:
                initiator, target_faction, initiator_type_resource, target_type_resource, \
                    initiator_summ_resource, target_summ_resource = row

                # Если текущая фракция является инициатором сделки
                if initiator == self.faction:
                    # Отнимаем ресурс, который отдает инициатор
                    if initiator_type_resource in self.resources:
                        self.resources[initiator_type_resource] -= initiator_summ_resource

                    # Добавляем ресурс, который получает инициатор
                    if target_type_resource in self.resources:
                        self.resources[target_type_resource] += target_summ_resource

                # Если текущая фракция является целевой фракцией
                elif target_faction == self.faction:
                    # Отнимаем ресурс, который отдает целевая фракция
                    if target_type_resource in self.resources:
                        self.resources[target_type_resource] -= target_summ_resource

                    # Добавляем ресурс, который получает целевая фракция
                    if initiator_type_resource in self.resources:
                        self.resources[initiator_type_resource] += initiator_summ_resource

            print(f"Ресурсы из торговых соглашений обновлены: {self.resources}")
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении ресурсов из торговых соглашений: {e}")
        except ValueError as ve:
            print(f"Ошибка в данных: {ve}")

    def load_resources_from_db(self):
        """
        Загружает текущие значения ресурсов из базы данных.
        Обновляет глобальные переменные self.money, self.free_peoples,
        self.raw_material, self.population и словарь self.resources.
        """
        try:
            query = "SELECT resource_type, amount FROM resources WHERE faction = ?"
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            # Обновление ресурсов на основе данных из базы данных
            for row in rows:
                resource_type, amount = row
                if resource_type == "Кроны":
                    self.money = amount
                elif resource_type == "Рабочие":
                    self.free_peoples = amount
                elif resource_type == "Сырье":
                    self.raw_material = amount
                elif resource_type == "Население":
                    self.population = amount

            # Обновление словаря self.resources
            self.resources = {
                'Кроны': self.money,
                'Рабочие': self.free_peoples,
                'Сырье': self.raw_material,
                'Население': self.population
            }

            print(f"Ресурсы успешно загружены из БД: {self.resources}")
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке ресурсов из БД: {e}")

    def update_resources(self):
        """
        Обновление текущих ресурсов с учетом данных из базы данных.
        Все расчеты выполняются на основе таблиц в базе данных.
        """
        try:
            self.update_buildings_from_db()

            # Генерируем новую цену на сырье
            self.generate_raw_material_price()

            # Обновляем ресурсы на основе торговых соглашений из таблицы trade_agreements
            self.update_trade_resources_from_db()

            self.process_trade_agreements()

            # Коэффициенты для каждой фракции
            faction_coefficients = {
                'Аркадия': {'money_loss': 100, 'food_loss': 0.4},
                'Селестия': {'money_loss': 10, 'food_loss': 0.04},
                'Хиперион': {'money_loss': 5, 'food_loss': 0.03},
                'Этерия': {'money_loss': 100, 'food_loss': 0.07},
                'Халидон': {'money_loss': 100, 'food_loss': 0.06},
            }

            # Получение коэффициентов для текущей фракции
            faction = self.faction
            if faction not in faction_coefficients:
                raise ValueError(f"Фракция '{faction}' не найдена.")
            coeffs = faction_coefficients[faction]

            # Обновление ресурсов с учетом коэффициентов
            self.born_peoples = int(self.hospitals * 500)
            self.work_peoples = int(self.factories * 200)
            self.clear_up_peoples = (self.born_peoples - self.work_peoples + self.tax_effects) + int(
                self.city_count * (self.population / 100))

            # Загружаем текущие значения ресурсов из базы данных
            self.load_resources_from_db()

            # Выполняем расчеты
            self.free_peoples += self.clear_up_peoples
            self.money += int(self.calculate_tax_income() - (self.hospitals * coeffs['money_loss']))
            self.money_info = int(self.hospitals * coeffs['money_loss'])
            self.money_up = int(self.calculate_tax_income() - (self.hospitals * coeffs['money_loss']))
            self.taxes_info = int(self.calculate_tax_income())

            # Учитываем, что одна фабрика может прокормить 10000 людей
            self.raw_material += int((self.factories * 1000) - (self.population * coeffs['food_loss']))
            self.food_info = (
                    int((self.factories * 1000) - (self.population * coeffs['food_loss'])) - self.total_consumption)
            self.food_peoples = int(self.population * coeffs['food_loss'])

            # Проверяем, будет ли население увеличиваться
            if self.raw_material > 0:
                self.population += int(self.clear_up_peoples)  # Увеличиваем население только если есть Сырье
            else:
                # Логика убыли населения при недостатке Сырья
                if self.population > 100:
                    loss = int(self.population * 0.45)  # 45% от населения
                    self.population -= loss
                else:
                    loss = min(self.population, 50)  # Обнуление по 50, но не ниже 0
                    self.population -= loss
                self.free_peoples = 0  # Все рабочие обнуляются, так как Сырья нет

            # Проверка, чтобы ресурсы не опускались ниже 0 и не превышали максимальные значения
            self.resources.update({
                "Кроны": max(min(int(self.money), 10_000_000_000), 0),  # Не более 10 млрд
                "Рабочие": max(min(int(self.free_peoples), 10_000_000), 0),  # Не более 10 млн
                "Сырье": max(min(int(self.raw_material), 10_000_000_000), 0),  # Не более 10 млрд
                "Население": max(min(int(self.population), 100_000_000), 0),  # Не более 100 млн
                "Текущее потребление": self.total_consumption,  # Используем рассчитанное значение
                "Лимит армии": self.army_limit
            })
            self.money = self.resources['Кроны']
            self.free_peoples = self.resources['Рабочие']
            self.raw_material = self.resources['Сырье']
            self.population = self.resources['Население']
            self.army_limit = self.resources['Лимит армии']
            self.total_consumption = self.resources['Текущее потребление']
            # Потребление армии
            self.calculate_and_deduct_consumption()

            self.save_resources_to_db()

            print(f"Ресурсы обновлены: {self.resources}, Больницы: {self.hospitals}, Фабрики: {self.factories}")

        except sqlite3.Error as e:
            print(f"Ошибка при обновлении ресурсов: {e}")

    def save_all_data(self):
        try:
            self.save_resources_to_db()
            self.save_buildings()
            self.save_results_to_db()
            print("Все данные успешно сохранены в БД")
        except Exception as e:
            print(f"Ошибка при сохранении данных: {e}")

    def get_unit_image(self, unit_name):
        """
        Получает путь к изображению юнита из базы данных.

        Args:
            unit_name (str): Название юнита

        Returns:
            str: Путь к изображению юнита или пустая строка, если не найдено
        """
        try:
            query = """
                SELECT image_path 
                FROM units 
                WHERE faction = ? AND unit_name = ?
            """
            self.cursor.execute(query, (self.faction, unit_name))
            result = self.cursor.fetchone()
            if result:
                return result[0]  # Возвращаем путь к изображению
            else:
                print(f"Предупреждение: Изображение для юнита '{unit_name}' не найдено")
                return ""
        except Exception as e:
            print(f"Ошибка при получении изображения юнита '{unit_name}': {e}")
            return ""

    def process_trade_agreements(self):
        """
        Обрабатывает торговые соглашения для текущей фракции.
        Если текущая фракция является target_faction, анализирует сделку и принимает решение.
        """
        try:
            # Загружаем текущие отношения с другими фракциями
            self.relations = self.load_relations()

            # Запрос для получения всех торговых соглашений, где текущая фракция является целевой
            query = """
                SELECT id, initiator, target_faction, initiator_type_resource, target_type_resource,
                       initiator_summ_resource, target_summ_resource
                FROM trade_agreements
                WHERE target_faction = ?
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            for row in rows:
                trade_id, initiator, target_faction, initiator_type_resource, target_type_resource, \
                    initiator_summ_resource, target_summ_resource = row

                # Проверяем уровень отношений с инициатором сделки
                relation_level = int(self.relations.get(initiator, 0))

                # Определяем коэффициент на основе уровня отношений
                if relation_level < 15:
                    print(f"Отказ от сделки с {initiator}. Низкий уровень отношений ({relation_level}).")
                    self.update_agreement_status(trade_id, False)  # Проставляем agree = false
                    continue

                # Проверяем наличие ресурсов у целевой фракции
                has_enough_resources = self.resources.get(target_type_resource, 0) >= target_summ_resource

                if not has_enough_resources:
                    print(f"Отказ от сделки с {initiator}. Недостаточно ресурсов для выполнения сделки.")
                    self.update_agreement_status(trade_id, False)  # Проставляем agree = false
                    continue

                # Рассчитываем соотношение обмена ресурсов
                resource_ratio = target_summ_resource / initiator_summ_resource

                # Определяем коэффициент выгодности сделки на основе отношений
                if relation_level < 25:
                    coefficient = 0.09
                elif 25 <= relation_level < 35:
                    coefficient = 0.2
                elif 35 <= relation_level < 50:
                    coefficient = 0.8
                elif 50 <= relation_level < 60:
                    coefficient = 1.0
                elif 60 <= relation_level < 75:
                    coefficient = 1.4
                elif 75 <= relation_level < 90:
                    coefficient = 2.0
                elif 90 <= relation_level <= 100:
                    coefficient = 3.1
                else:
                    coefficient = 0.0

                # Проверяем, выгодна ли сделка
                if resource_ratio > coefficient:
                    print(
                        f"Отказ от сделки с {initiator}. Не выгодное соотношение ({resource_ratio:.2f} < {coefficient:.2f})."
                    )
                    self.update_agreement_status(trade_id, False)  # Проставляем agree = false
                    continue

                # Если сделка выгодна, выполняем обмен ресурсами
                print(
                    f"Принята сделка с {initiator}. Соотношение: {resource_ratio:.2f}, Коэффициент: {coefficient:.2f}."
                )
                self.execute_trade(initiator, target_faction, initiator_type_resource, target_type_resource,
                                   initiator_summ_resource, target_summ_resource)
                self.update_agreement_status(trade_id, True)  # Проставляем agree = true

        except sqlite3.Error as e:
            print(f"Ошибка при обработке торговых соглашений: {e}")

    def update_agreement_status(self, trade_id, status):
        """
        Обновляет значение agree в таблице trade_agreements.
        :param trade_id: ID торгового соглашения
        :param status: True или False
        """
        try:
            query = """
                UPDATE trade_agreements
                SET agree = ?
                WHERE id = ?
            """
            self.cursor.execute(query, (status, trade_id))
            self.db_connection.commit()
            print(f"Статус сделки ID={trade_id} обновлен: agree={status}")
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении статуса сделки: {e}")

    def return_resource_to_player(self, initiator, resource_type, amount):
        """
        Возвращает ресурсы инициатору сделки в случае отказа.
        """
        try:
            self.cursor.execute("""
                UPDATE resources
                SET amount = amount + ?
                WHERE faction = ? AND resource_type = ?
            """, (amount, initiator, resource_type))
            self.db_connection.commit()
            print(f"Возвращено {amount} {resource_type} фракции {initiator}.")
        except sqlite3.Error as e:
            print(f"Ошибка при возврате ресурсов: {e}")

    def remove_trade_agreement(self, trade_id):
        """
        Удаляет торговое соглашение из базы данных.
        """
        try:
            self.cursor.execute("""
                DELETE FROM trade_agreements
                WHERE id = ?
            """, (trade_id,))
            self.db_connection.commit()
            print(f"Торговое соглашение ID={trade_id} удалено.")
        except sqlite3.Error as e:
            print(f"Ошибка при удалении торгового соглашения: {e}")

    def execute_trade(self, initiator, target_faction, initiator_type_resource, target_type_resource,
                      initiator_summ_resource, target_summ_resource):
        """
        Выполняет обмен ресурсами между фракциями.
        """
        try:
            # Отнимаем ресурсы у инициатора
            self.cursor.execute("""
                UPDATE resources
                SET amount = amount - ?
                WHERE faction = ? AND resource_type = ?
            """, (initiator_summ_resource, initiator, initiator_type_resource))

            # Добавляем ресурсы целевой фракции
            self.cursor.execute("""
                UPDATE resources
                SET amount = amount + ?
                WHERE faction = ? AND resource_type = ?
            """, (target_summ_resource, target_faction, target_type_resource))

            # Добавляем ресурсы целевой фракции инициатору
            self.cursor.execute("""
                UPDATE resources
                SET amount = amount + ?
                WHERE faction = ? AND resource_type = ?
            """, (initiator_summ_resource, target_faction, initiator_type_resource))

            # Отнимаем ресурсы у целевой фракции
            self.cursor.execute("""
                UPDATE resources
                SET amount = amount - ?
                WHERE faction = ? AND resource_type = ?
            """, (target_summ_resource, initiator, target_type_resource))

            self.db_connection.commit()
            print(f"Обмен ресурсами выполнен: {initiator} <-> {target_faction}.")
        except sqlite3.Error as e:
            print(f"Ошибка при выполнении обмена ресурсами: {e}")

    def load_political_system(self):
        """
        Загружает текущую политическую систему фракции из базы данных.
        """
        try:
            query = "SELECT system FROM political_systems WHERE faction = ?"
            self.cursor.execute(query, (self.faction,))
            result = self.cursor.fetchone()
            return result[0] if result else "Капитализм"  # По умолчанию "Капитализм"
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке политической системы: {e}")
            return "Капитализм"

    def calculate_army_strength(self):
        """
        Рассчитывает силу армий для каждой фракции.
        :return: Словарь, где ключи — названия фракций, а значения — сила армии.
        """
        class_coefficients = {
            "1": 1.3,  # Класс 1: базовые юниты
            "2": 1.7,  # Класс 2: улучшенные юниты
            "3": 2.0,  # Класс 3: элитные юниты
            "4": 3.0  # Класс 4: легендарные юниты
        }

        army_strength = {}

        try:
            # Получаем все юниты из таблицы garrisons и их характеристики из таблицы units
            query = """
                SELECT g.unit_name, g.unit_count, u.faction, u.attack, u.defense, u.durability, u.unit_class 
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
            """
            self.cursor.execute(query)
            garrison_data = self.cursor.fetchall()

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

        except sqlite3.Error as e:
            print(f"Ошибка при расчете силы армии: {e}")
            return {}

        return army_strength

    def notify_player_about_war(self, faction):
        """
        Создает уведомление для игрока о том, что фракция объявила войну.
        :param faction: Название фракции
        """
        try:
            # Здесь можно интегрировать логику для отображения окна уведомления
            print(f"!!! ВНИМАНИЕ !!! Фракция {self.faction} объявила войну фракции {faction}.")
            # Пример: вызов GUI-функции для отображения уведомления
            # show_notification(f"Фракция {self.faction} объявила войну!")
        except Exception as e:
            print(f"Ошибка при уведомлении игрока: {e}")

    def update_diplomacy_status(self, faction, status):
        """
        Обновляет статус дипломатии с указанной фракцией.
        :param faction: Название фракции
        :param status: Новый статус ("война" или "мир")
        """
        try:
            # Обновляем запись A-B
            query = """
                UPDATE diplomacies
                SET relationship = ?
                WHERE faction1 = ? AND faction2 = ?
            """
            self.cursor.execute(query, (status, self.faction, faction))

            # Обновляем запись B-A
            query = """
                UPDATE diplomacies
                SET relationship = ?
                WHERE faction1 = ? AND faction2 = ?
            """
            self.cursor.execute(query, (status, faction, self.faction))

            self.db_connection.commit()
            print(f"Статус дипломатии между {self.faction} и {faction} обновлен на '{status}'.")
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении статуса дипломатии: {e}")

    def find_nearest_allied_city(self, faction):
        """
        Находит ближайший союзный город для передислокации войск.
        :param faction: Название фракции (своей или союзной)
        :return: Имя ближайшего союзного города или None, если подходящий город не найден
        """
        try:
            # Получаем координаты всех городов текущей фракции
            query = "SELECT name, coordinates FROM cities WHERE faction = ?"
            self.cursor.execute(query, (self.faction,))
            our_cities = self.cursor.fetchall()

            # Получаем координаты всех союзных городов
            query = "SELECT name, coordinates FROM cities WHERE faction = ?"
            self.cursor.execute(query, (faction,))
            allied_cities = self.cursor.fetchall()

            # Находим ближайший союзный город с учетом ограничения по дистанции
            nearest_city = None
            for our_city_name, our_coords in our_cities:
                our_coords = our_coords.strip("[]")  # Убираем [ и ]
                our_x, our_y = map(int, our_coords.split(','))
                for allied_city_name, allied_coords in allied_cities:
                    allied_coords = allied_coords.strip("[]")  # Убираем [ и ]
                    allied_x, allied_y = map(int, allied_coords.split(','))
                    distance = ((our_x - allied_x) ** 2 + (our_y - allied_y) ** 2) ** 0.5
                    if distance <= 225:
                        nearest_city = allied_city_name
            return nearest_city
        except sqlite3.Error as e:
            print(f"Ошибка при поиске ближайшего союзного города: {e}")
            return None

    def find_nearest_city(self, faction):
        """Находит ближайший город противника для атаки.
        :param faction: Название фракции
        :return: Имя ближайшего города или None, если подходящий город не найден"""
        try:
            # Получаем координаты всех городов текущей фракции
            query = "SELECT name, coordinates FROM cities WHERE faction = ?"
            self.cursor.execute(query, (self.faction,))
            our_cities = self.cursor.fetchall()

            # Получаем координаты всех городов противника
            query = "SELECT name, coordinates FROM cities WHERE faction = ?"
            self.cursor.execute(query, (faction,))
            enemy_cities = self.cursor.fetchall()

            nearest_city = None

            for our_city_name, our_coords in our_cities:
                our_coords = our_coords.strip("[]")  # Убираем [ и ]
                our_x, our_y = map(int, our_coords.split(','))

                for enemy_city_name, enemy_coords in enemy_cities:
                    enemy_coords = enemy_coords.strip("[]")  # Убираем [ и ]
                    enemy_x, enemy_y = map(int, enemy_coords.split(','))

                    # Новый расчет расстояния
                    distance = abs(our_x - enemy_x) + abs(our_y - enemy_y)

                    if distance < 225:
                        nearest_city = enemy_city_name
                        return nearest_city

            return None
        except sqlite3.Error as e:
            print(f"Ошибка при поиске ближайшего города: {e}")
            return None



    def relocate_units(self, from_city_name, to_city_name, unit_name, unit_count, unit_image):
        try:
            # Проверяем, что города разные
            if from_city_name == to_city_name:
                print(f"Передислокация в тот же город невозможна: {from_city_name}")
                return

            # Уменьшаем количество юнитов в исходном городе
            self.cursor.execute("""
                UPDATE garrisons
                SET unit_count = unit_count - ?
                WHERE city_id = ? AND unit_name = ?
            """, (unit_count, from_city_name, unit_name))

            # Удаляем запись, если юнитов больше нет
            self.cursor.execute("""
                DELETE FROM garrisons
                WHERE city_id = ? AND unit_name = ? AND unit_count <= 0
            """, (from_city_name, unit_name))

            # Добавляем юниты в целевой город
            self.cursor.execute("""
                INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(city_id, unit_name) DO UPDATE SET
                unit_count = unit_count + excluded.unit_count,
                unit_image = excluded.unit_image
            """, (to_city_name, unit_name, unit_count, unit_image))

            self.db_connection.commit()
            print(f"Передислокация {unit_count} юнитов {unit_name} из {from_city_name} в {to_city_name} выполнена.")
        except sqlite3.Error as e:
            print(f"Ошибка при передислокации: {e}")

    def launch_attack_on_city(self, city_name, faction):
        try:
            # Проверяем, является ли атака результатом запроса союзника
            is_ally_request = self.is_faction_ally(faction)

            attacking_units = self.collect_attacking_units()
            if not attacking_units:
                print("Нет атакующих юнитов.")
                return

            # Добавляем новую логику после сбора юнитов
            if is_ally_request:
                # Получаем фракцию-владельца города
                self.cursor.execute("""
                    SELECT faction FROM cities WHERE name = ?
                """, (city_name,))
                target_faction = self.cursor.fetchone()[0]

                # Обновляем статус дипломатии на "война"
                self.update_diplomacy_status(target_faction, "война")

                # Обнуляем отношения в таблице relations
                self.cursor.execute("""
                    UPDATE relations
                    SET relationship = 0
                    WHERE faction1 = ? AND faction2 = ?
                """, (self.faction, target_faction))
                self.db_connection.commit()

                print(f"Фракция {self.faction} объявила войну фракции {target_faction} по запросу союзника.")

            total_units = sum(unit["unit_count"] for unit in attacking_units)
            units_to_attack = int(total_units * 0.6)
            remaining_units = units_to_attack

            attack_army = []
            for unit in attacking_units:
                if remaining_units <= 0:
                    break
                # Берем все доступные юниты из города, если нужно
                take_units = min(unit["unit_count"], remaining_units)
                attack_army.append({
                    "city_id": unit["city_id"],
                    "unit_name": unit["unit_name"],
                    "unit_count": take_units,
                    "unit_image": unit["unit_image"]
                })
                remaining_units -= take_units

            # Передислоцируем все собранные юниты в союзный город
            allied_city = self.find_nearest_allied_city(self.faction)
            if not allied_city:
                print("Союзный город не найден.")
                return

            for unit in attack_army:
                self.relocate_units(
                    from_city_name=unit["city_id"],
                    to_city_name=allied_city,
                    unit_name=unit["unit_name"],
                    unit_count=unit["unit_count"],
                    unit_image=unit["unit_image"]
                )

            # Атакуем город
            self.attack_city(city_name, faction)
        except Exception as e:
            print(f"Ошибка при атаке: {e}")

    def get_defending_army(self, city_name):
        """
        Получает данные об обороняющейся армии в указанном городе.
        :param city_name: Имя города
        :return: Список обороняющихся юнитов
        """
        try:
            query = """
                SELECT g.unit_name, g.unit_count, u.attack, u.defense, u.durability, u.unit_class, g.unit_image
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE g.city_id = ?
            """
            self.cursor.execute(query, (city_name,))
            defending_units = self.cursor.fetchall()

            defending_army = []
            for unit_name, unit_count, attack, defense, durability, unit_class, unit_image in defending_units:
                defending_army.append({
                    "unit_name": unit_name,
                    "unit_count": int(unit_count),
                    "unit_image": unit_image,
                    "units_stats": {
                        "Урон": int(attack),
                        "Защита": int(defense),
                        "Живучесть": int(durability),
                        "Класс юнита": unit_class,
                    }
                })
            return defending_army
        except sqlite3.Error as e:
            print(f"Ошибка при получении обороняющейся армии: {e}")
            return []

    def attack_city(self, city_name, faction):
        try:
            # Находим ближайший союзный город для атаки
            allied_city = self.find_nearest_allied_city(self.faction)
            if not allied_city:
                print("Не удалось найти ближайший союзный город.")
                return

            print(f"Ближайший союзный город для атаки: {allied_city}")

            # Собираем все атакующие юниты из всех городов
            attacking_units = self.collect_attacking_units()
            if not attacking_units:
                print("Нет подходящих юнитов для атаки.")
                return

            # Передислоцируем юниты в ближайший союзный город
            for unit in attacking_units:
                self.relocate_units(
                    from_city_name=unit["city_id"],
                    to_city_name=allied_city,
                    unit_name=unit["unit_name"],
                    unit_count=unit["unit_count"],
                    unit_image=unit["unit_image"]
                )

            print(f"Все атакующие юниты передислоцированы в город {allied_city}.")

            # Проверяем общую численность войск в городе атаки
            self.cursor.execute("""
                SELECT SUM(unit_count) FROM garrisons WHERE city_id = ?
            """, (allied_city,))
            total_units = self.cursor.fetchone()[0] or 0

            if total_units == 0:
                print("Войска не готовы к атаке. Гарнизон пуст.")
                return

            # Формируем армию для атаки
            attacking_army = []
            for unit in attacking_units:
                self.cursor.execute("""
                    SELECT attack, defense, durability, unit_class
                    FROM units
                    WHERE unit_name = ?
                """, (unit["unit_name"],))
                stats = self.cursor.fetchone()
                if stats:
                    attacking_army.append({
                        "unit_name": unit["unit_name"],
                        "unit_count": unit["unit_count"],
                        "unit_image": unit["unit_image"],
                        "units_stats": {
                            "Урон": stats[0],
                            "Защита": stats[1],
                            "Живучесть": stats[2],
                            "Класс юнита": stats[3],
                        }
                    })

            # Атакуем вражеский город
            result = fight(
                attacking_city=allied_city,
                defending_city=city_name,
                defending_army=self.get_defending_army(city_name),
                attacking_army=attacking_army,
                attacking_fraction=self.faction,
                defending_fraction=faction,
                db_connection=self.db_connection
            )
            print(f"Результат битвы: {result}")

            # Обработка результата битвы
            if result["winner"] == "attacker":
                self.army_efficiency_ratio = result["efficiency_ratio"]

                # Распределяем войска после победы
                defensive_units = []
                remaining_units = []

                for unit in attacking_army:
                    defense = unit["units_stats"]["Защита"]
                    unit_count = unit["unit_count"]

                    # Разделяем войска на оборонительные и атакующие
                    if defense > 50:  # Юниты с высокой защитой
                        defensive_units.append(unit)
                    else:
                        remaining_units.append(unit)

                # Размещаем 30% сил с высокой защитой в захваченном городе
                for unit in defensive_units:
                    defense_count = int(unit["unit_count"] * 0.3)
                    if defense_count > 0:
                        self.relocate_units(allied_city, city_name, unit["unit_name"], defense_count,
                                            unit["unit_image"])
                        print(
                            f"Размещено {defense_count} юнитов '{unit['unit_name']}' в городе {city_name} для обороны.")

                # Отводим остальные войска обратно в союзный город
                for unit in remaining_units:
                    remaining_count = unit["unit_count"]
                    if remaining_count > 0:
                        self.relocate_units(allied_city, allied_city, unit["unit_name"], remaining_count,
                                            unit["unit_image"])
                        print(f"Отведено {remaining_count} юнитов '{unit['unit_name']}' обратно в город {allied_city}.")

                # Обновляем принадлежность города
                self.cursor.execute("""
                    UPDATE cities
                    SET faction = ?
                    WHERE name = ?
                """, (self.faction, city_name))

                print(f"Город {city_name} захвачен и укреплен оборонительными войсками.")
            else:
                print(f"Атака на город {city_name} провалилась.")

        except Exception as e:
            print(f"Ошибка при атаке города: {e}")

    def capture_city(self, city_name):
        """
        Захватывает город под контроль текущей фракции.
        :param city_name: Название захваченного города
        """
        print("---------------------------------")
        print("city_name", city_name)
        print("---------------------------------")
        try:
            with self.db_connection:
                # Удаляем гарнизон противника
                self.cursor.execute("""
                    DELETE FROM garrisons WHERE city_id = ?
                """, (city_name,))

                # Перемещаем атакующую армию в захваченный город
                for unit in self.attacking_army:
                    self.cursor.execute("""
                        INSERT INTO garrisons (city_id, unit_name, unit_count, unit_image)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(city_id, unit_name) DO UPDATE SET
                        unit_count = excluded.unit_count,
                        unit_image = excluded.unit_image
                    """, (
                        city_name,
                        unit['unit_name'],
                        unit['unit_count'],
                        self.get_unit_image(unit['unit_name'])
                    ))

                # Обновляем принадлежность города в таблице cities
                self.cursor.execute("""
                    UPDATE cities
                    SET faction = ?
                    WHERE name = ?
                """, (self.faction, city_name))

                self.cursor.execute("""
                    UPDATE city
                    SET kingdom = ?
                    WHERE fortress_name = ?
                """, (self.faction, city_name))

                # Обновляем принадлежность зданий
                self.cursor.execute("""
                    UPDATE buildings
                    SET faction = ?
                    WHERE city_id = ?
                """, (self.faction, city_name))

                print(f"Город {city_name} успешно захвачен фракцией {self.faction}.")
        except sqlite3.Error as e:
            print(f"Ошибка при захвате города: {e}")

    def update_buildings_for_current_cities(self):
        """
        Обновляет self.buildings, учитывая только города, которые на данный момент принадлежат фракции.
        """
        try:
            # Загружаем актуальный список городов текущей фракции
            query = """
                SELECT id, name 
                FROM cities 
                WHERE faction = ?
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()
            current_cities = {row[0]: row[1] for row in rows}

            # Очищаем self.buildings и обновляем его только для актуальных городов
            updated_buildings = {}
            for city_id, city_name in current_cities.items():
                updated_buildings[city_name] = {"Здания": {"Больница": 0, "Фабрика": 0}}

            # Загружаем данные о зданиях для актуальных городов
            query = """
                SELECT city_name, building_type, count 
                FROM buildings 
                WHERE faction = ?
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            for row in rows:
                city_name, building_type, count = row
                if city_name in updated_buildings:
                    updated_buildings[city_name]["Здания"][building_type] += count

            # Обновляем self.buildings
            self.buildings = updated_buildings
            print(f"Обновлены данные о зданиях для фракции {self.faction}: {self.buildings}")

        except sqlite3.Error as e:
            print(f"Ошибка при обновлении данных о зданиях: {e}")

    def check_for_empty_garrison(self, city_id, faction):
        """
        Проверяет, остались ли в городе юниты противника.
        Если гарнизон пуст, город переходит под контроль текущей фракции.
        :param city_id: ID города
        :param faction: Фракция противника
        """
        try:
            # Проверяем количество юнитов противника в гарнизоне
            self.cursor.execute("""
                SELECT SUM(unit_count) FROM garrisons
                WHERE city_id = ? AND faction = ?
            """, (city_id, faction))
            total_units = self.cursor.fetchone()[0] or 0

            if total_units == 0:
                print(f"Гарнизон противника в городе ID={city_id} уничтожен. Город переходит под контроль ИИ.")
                self.capture_city(city_id)
        except sqlite3.Error as e:
            print(f"Ошибка при проверке гарнизона: {e}")

    def check_and_declare_war(self):
        """
        Проверяет уровень отношений с другими фракциями.
        Если отношения падают ниже 12% И сила армии потенциального противника
        ниже в 1.5 раза, чем сила текущей фракции, объявляет войну.
        Также проверяет, находится ли фракция в состоянии войны, и если да,
        сразу атакует ближайший город.
        """
        try:
            # Загружаем текущие отношения с другими фракциями
            self.relations = self.load_relations()
            # Рассчитываем силу армий для всех фракций
            army_strength = self.calculate_army_strength()
            our_strength = army_strength.get(self.faction, 0)
            print("our_strength:", type(our_strength), our_strength)

            for faction, relationship in self.relations.items():
                # Проверяем текущий статус дипломатии с фракцией
                query = """
                    SELECT relationship FROM diplomacies
                    WHERE faction1 = ? AND faction2 = ?
                """
                self.cursor.execute(query, (self.faction, faction))
                result = self.cursor.fetchone()

                if result is None:
                    # Если записи нет, считаем, что статус "мир"
                    diplomacy_status = "мир"
                    print(f"Дипломатический статус с фракцией {faction} не найден. Установлен статус 'мир'.")
                else:
                    diplomacy_status = result[0]

                if diplomacy_status == "война":
                    # Если уже объявлена война, атакуем ближайший город
                    print(f"Фракция {self.faction} уже находится в состоянии войны с фракцией {faction}.")
                    target_city = self.find_nearest_city(faction)
                    if target_city:
                        print(f"Ближайший вражеский город для атаки: {target_city}")
                        self.attack_city(target_city, faction)
                    else:
                        print(f"Не удалось найти подходящий город для атаки у фракции {faction}.")
                    continue

                # Если нет войны, проверяем условия для объявления войны
                if int(relationship) < 12:  # Если отношения ниже 12%
                    enemy_strength = army_strength.get(faction, 0)
                    # Проверяем, что наша сила армии больше в 1.4 раза
                    if our_strength > 1.4 * enemy_strength:
                        print(f"Отношения с фракцией {faction} упали ниже 12%. "
                              f"Сила нашей армии: {our_strength}, сила противника: {enemy_strength}. Объявление войны.")
                        # Обновляем статус дипломатии на "война"
                        self.update_diplomacy_status(faction, "война")
                        # Уведомляем игрока о начале войны
                        self.notify_player_about_war(faction)
                        # Определяем ближайший город для атаки
                        target_city = self.find_nearest_city(faction)
                        if target_city:
                            print(f"Ближайший вражеский город для атаки: {target_city}")
                            # Наносим удар по ближайшему городу
                            self.attack_city(target_city, faction)
                        else:
                            print(f"Не удалось найти подходящий город для атаки у фракции {faction}.")
                    else:
                        print(f"Отношения с фракцией {faction} упали ниже 12%, "
                              f"но сила противника слишком велика. Война не объявлена.")
        except Exception as e:
            print(f"Ошибка при проверке и объявлении войны: {e}")

    def process_queries(self):
        """
        Обрабатывает запросы из таблицы queries.
        Для каждого запроса проверяет, является ли фракция союзником,
        и выполняет соответствующие действия на основе заполненных столбцов.
        После обработки всех запросов очищает таблицу queries, только если ходит союзник.
        """
        try:
            # Загружаем все запросы из таблицы queries
            query = """
                SELECT resource, defense_city, attack_city, faction
                FROM queries
            """
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            is_ally_turn = False  # Флаг для отслеживания, был ли ход союзника

            for row in rows:
                resource, defense_city, attack_city, faction = row

                # Проверяем, является ли фракция союзником
                is_ally = self.is_faction_ally(faction)

                if not is_ally:
                    print(f"Фракция {faction} не является союзником. Пропускаем запрос.")
                    continue

                is_ally_turn = True  # Устанавливаем флаг, если хотя бы один запрос выполнен для союзника

                # Если заполнен столбец resource
                if resource:
                    self.transfer_resource_to_ally(faction, resource)

                # Если заполнен столбец defense_city
                if defense_city:
                    self.reinforce_defense_in_city(defense_city, faction)

                # Если заполнен столбец attack_city
                if attack_city:
                    # Получаем владельца целевого города
                    self.cursor.execute("""
                        SELECT faction FROM cities WHERE name = ?
                    """, (attack_city,))
                    target_faction = self.cursor.fetchone()[0]

                    # Обновляем статус дипломатии на "война"
                    self.update_diplomacy_status(target_faction, "война")

                    # Обнуляем отношения в таблице relations
                    self.cursor.execute("""
                        UPDATE relations
                        SET relationship = 0
                        WHERE faction1 = ? AND faction2 = ?
                    """, (self.faction, target_faction))
                    self.db_connection.commit()

                    print(f"Фракция {self.faction} объявила войну фракции {target_faction} по запросу союзника.")

                    # Выполняем атаку на город
                    self.launch_attack_on_city(attack_city, faction)

            # Очищаем таблицу queries, только если был ход союзника
            if is_ally_turn:
                self.clear_queries_table()
                print("Обработка запросов завершена. Таблица queries очищена.")
            else:
                print("Обработка запросов завершена. Таблица queries не очищена, так как ходили не союзники.")

        except sqlite3.Error as e:
            print(f"Ошибка при обработке запросов: {e}")

    def clear_queries_table(self):
        """
        Очищает таблицу queries.
        """
        try:
            query = "DELETE FROM queries"
            self.cursor.execute(query)
            self.db_connection.commit()
            print("Таблица queries успешно очищена.")
        except sqlite3.Error as e:
            print(f"Ошибка при очистке таблицы queries: {e}")

    def is_faction_ally(self, faction):
        """
        Проверяет, является ли указанная фракция союзником текущей фракции.
        :param faction: Название фракции
        :return: True, если союзник ('союз'); False, если нет
        """
        try:
            # Загружаем статус дипломатии с указанной фракцией
            query = """
                SELECT relationship
                FROM diplomacies
                WHERE faction1 = ? AND faction2 = ?
            """
            self.cursor.execute(query, (self.faction, faction))
            result = self.cursor.fetchone()

            # Если запись найдена и статус равен 'союз', возвращаем True
            if result and result[0] == 'союз':
                return True

            # Во всех остальных случаях возвращаем False
            return False
        except sqlite3.Error as e:
            print(f"Ошибка при проверке союзника: {e}")
            return False

    def transfer_resource_to_ally(self, faction, resource_type):
        """
        Передает 40% ресурса указанного типа союзной фракции.
        Данные о передаче записываются в таблицу trade_agreements.
        :param faction: Название союзной фракции (target_faction)
        :param resource_type: Тип ресурса (initiator_type_resource и target_type_resource)
        """
        try:
            # Получаем текущее количество ресурса у текущей фракции
            current_amount = self.resources.get(resource_type, 0)
            if current_amount <= 0:
                print(f"Нет доступных ресурсов типа {resource_type} для передачи.")
                return

            # Вычисляем 40% от текущего количества ресурса
            amount_to_transfer = int(current_amount * 0.4)

            # Уменьшаем количество ресурса у текущей фракции
            self.resources[resource_type] -= amount_to_transfer

            # Записываем данные о передаче в таблицу trade_agreements
            self.cursor.execute("""
                INSERT INTO trade_agreements (
                    initiator, 
                    target_faction, 
                    initiator_type_resource, 
                    initiator_summ_resource, 
                    target_type_resource, 
                    target_summ_resource,
                    agree
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.faction,  # initiator (текущая фракция)
                faction,  # target_faction (союзная фракция)
                resource_type,  # initiator_type_resource (тип ресурса)
                amount_to_transfer,  # initiator_summ_resource (переданное количество)
                "",  # target_type_resource (тип ресурса у союзника)
                "",  # target_summ_resource (полученное количество)
                1  # agree (статус сделки
            ))

            # Сохраняем изменения в базе данных
            self.db_connection.commit()

            print(f"Передано {amount_to_transfer} {resource_type} союзной фракции {faction}.")
        except sqlite3.Error as e:
            print(f"Ошибка при передаче ресурсов: {e}")

    def reinforce_defense_in_city(self, city_name, faction):
        """
        Направляет 40% защитных юнитов в указанный город.
        :param city_name: Название города
        :param faction: Название союзной фракции
        """
        try:
            # Собираем защитные юниты из всех городов текущей фракции
            defensive_units = self.collect_defensive_units()

            if not defensive_units:
                print("Нет доступных защитных юнитов для передислокации.")
                return

            # Вычисляем 40% от общего количества защитных юнитов
            total_units = sum(unit["unit_count"] for unit in defensive_units)
            units_to_relocate = int(total_units * 0.4)

            # Распределяем юниты между городами
            relocated_units = []
            remaining_units = units_to_relocate
            for unit in defensive_units:
                if remaining_units <= 0:
                    break
                units_from_this = min(unit["unit_count"], remaining_units)
                relocated_units.append({
                    "city_id": unit["city_id"],  # Город отправления
                    "unit_name": unit["unit_name"],
                    "unit_count": units_from_this,
                    "unit_image": unit["unit_image"]
                })
                remaining_units -= units_from_this

            print('*******************************************relocated_units :', relocated_units)

            # Передислоцируем юниты в указанный город
            for unit in relocated_units:
                self.relocate_units(
                    from_city_name=unit["city_id"],
                    to_city_name=city_name,
                    unit_name=unit["unit_name"],
                    unit_count=unit["unit_count"],
                    unit_image=unit["unit_image"]
                )

            print(f"Передислоцировано {units_to_relocate} защитных юнитов в город {city_name}.")
        except Exception as e:
            print(f"Ошибка при усилении обороны: {e}")

    def collect_defensive_units(self):
        """
        Собирает защитные юниты из всех городов текущей фракции.
        :return: Список защитных юнитов с информацией о городе отправления
        """
        try:
            query = """
                SELECT g.city_id, g.unit_name, g.unit_count, u.defense, g.unit_image
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE u.faction = ? AND u.defense > u.attack
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()

            defensive_units = []
            for row in rows:
                city_id, unit_name, unit_count, defense, unit_image = row
                defensive_units.append({
                    "city_id": city_id,
                    "unit_name": unit_name,
                    "unit_count": unit_count,
                    "unit_image": unit_image
                })

            return defensive_units
        except sqlite3.Error as e:
            print(f"Ошибка при сборе защитных юнитов: {e}")
            return []
        except ValueError as ve:
            print(f"Ошибка при обработке данных: {ve}")
            return []


    def collect_attacking_units(self):
        try:
            query = """
                SELECT g.city_id, g.unit_name, g.unit_count, u.attack, g.unit_image
                FROM garrisons g
                JOIN units u ON g.unit_name = u.unit_name
                WHERE u.faction = ? AND u.attack > u.defense
            """
            self.cursor.execute(query, (self.faction,))
            rows = self.cursor.fetchall()
            attacking_units = []
            for row in rows:
                city_id, unit_name, unit_count, attack, unit_image = row
                print(f"Собран атакующий юнит: {unit_name}, Количество: {unit_count}, Атака: {attack}")
                attacking_units.append({
                    "city_id": city_id,
                    "unit_name": unit_name,
                    "unit_count": unit_count,
                    "unit_image": unit_image,
                })
            return attacking_units
        except sqlite3.Error as e:
            print(f"Ошибка при сборе атакующих юнитов: {e}")
            return []

    def apply_political_system_bonus(self):
        """
        Применяет бонусы от политической системы.
        """
        system = self.load_political_system()
        if system == "Капитализм":
            crowns_bonus = int(self.money_up * 1.65)
            self.resources['Кроны'] = int(self.resources.get('Кроны', 0)) + crowns_bonus
            print(f"Бонус от капитализма: +{crowns_bonus} Крон")
        elif system == "Коммунизм":
            raw_material_bonus = int(self.food_info * 2.25)
            self.resources['Сырье'] = int(self.resources.get('Сырье', 0)) + raw_material_bonus
            print(f"Бонус от коммунизма: +{raw_material_bonus} Сырья")

    def update_relations_based_on_political_system(self):
        """
        Изменяет отношения на основе политической системы каждые 3 хода.
        """
        if self.turn % 3 != 0:
            return

        current_system = self.load_political_system()
        all_factions = self.load_relations()

        for faction, relation_level in all_factions.items():
            other_system = self.load_political_system_for_faction(faction)

            # Преобразуем relation_level в число
            relation_level = int(relation_level)

            if current_system == other_system:
                new_relation = min(relation_level + 2, 100)
            else:
                new_relation = max(relation_level - 2, 0)

            self.update_relation_in_db(faction, new_relation)

    def load_political_system_for_faction(self, faction):
        """
        Загружает политическую систему указанной фракции.
        """
        try:
            query = "SELECT system FROM political_systems WHERE faction = ?"
            self.cursor.execute(query, (faction,))
            result = self.cursor.fetchone()
            return result[0] if result else "Капитализм"  # По умолчанию "Капитализм"
        except sqlite3.Error as e:
            print(f"Ошибка при загрузке политической системы для фракции {faction}: {e}")
            return "Капитализм"

    def update_relation_in_db(self, faction, new_relation):
        """
        Обновляет уровень отношений в базе данных.
        """
        try:
            query = """
                UPDATE relations
                SET relationship = ?
                WHERE faction1 = ? AND faction2 = ?
            """
            self.cursor.execute(query, (new_relation, self.faction, faction))
            self.db_connection.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении отношений для фракции {faction}: {e}")


    def update_economic_efficiency(self, efficiency_value):
        try:
            # Проверяем существование записи для фракции
            self.cursor.execute('''
                SELECT Average_Deal_Ratio
                FROM results 
                WHERE faction = ?
            ''', (self.faction,))
            row = self.cursor.fetchone()

            if row:
                # Если запись существует - обновляем среднее значение
                current_efficiency = row[0] if row[0] is not None else 0
                new_efficiency = (current_efficiency + efficiency_value) / 2
                self.average_deal_ratio = new_efficiency  # Обновляем атрибут
            else:
                # Если записи нет - сохраняем новое значение
                new_efficiency = efficiency_value
                self.average_deal_ratio = new_efficiency

            # Сохраняем в БД через метод save_results_to_db
            self.save_results_to_db()
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении экономической эффективности: {e}")

    def save_results_to_db(self):
        try:
            # Обновляем только коэффициент сделок
            self.cursor.execute('''SELECT Average_Deal_Ratio FROM results WHERE faction = ?''', (self.faction,))
            existing = self.cursor.fetchone()

            new_deal_ratio = self.average_deal_ratio

            if existing:
                updated_ratio = (existing[0] * 0.3 + new_deal_ratio * 0.7) if existing[0] else new_deal_ratio
                self.cursor.execute('''UPDATE results SET Average_Deal_Ratio = ? WHERE faction = ?''',
                                    (updated_ratio, self.faction))
            else:
                self.cursor.execute('''INSERT INTO results (Average_Deal_Ratio, faction) VALUES (?, ?)''',
                                    (new_deal_ratio, self.faction))

            self.db_connection.commit()
        except sqlite3.Error as e:
            print(f"Ошибка сохранения результатов: {e}")


    # ---------------------------------------------------------------------

    # Основная логика хода ИИ
    def make_turn(self):
        """
        Основная логика хода ИИ фракции.
        """
        print(f'---------ХОДИТ ФРАКЦИЯ: {self.faction}-------------------')
        try:
            # 1. Обновляем ресурсы из базы данных
            self.update_resources()
            self.process_queries()
            # 2. Проверяем и объявляем войну, если необходимо
            self.check_and_declare_war()
            # 3. Применяем бонусы от политической системы
            self.apply_political_system_bonus()
            # 4. Изменяем отношения на основе политической системы
            self.update_relations_based_on_political_system()
            # 5. Загружаем данные о зданиях
            self.update_buildings_from_db()
            # 6. Управление строительством (90% крон на строительство)
            self.manage_buildings()
            # 7. Продажа сырья (99% сырья, если его больше 10000)
            resources_sold = self.sell_resources()
            # 8. Найм армии (на оставшиеся деньги после строительства и продажи сырья)
            if resources_sold:
                self.hire_army()
            # 9. Сохраняем все изменения в базу данных
            self.save_all_data()
            # Увеличиваем счетчик ходов
            self.turn += 1
            print(f'-----------КОНЕЦ {self.turn} ХОДА----------------  ФРАКЦИИ', self.faction)
        except Exception as e:
            print(f"Ошибка при выполнении хода: {e}")
