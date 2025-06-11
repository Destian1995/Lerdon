# seasons.py

import sqlite3
from db_lerdon_connect import db_path

class SeasonManager:
    """
    Менеджер сезонов, теперь с учётом фракций.

    При первом вызове update(new_idx) просто накладывается эффект для сезона new_idx.
    При смене с last_idx на new_idx:
      1. Откатываем всё, что накладывалось для last_idx (_revert_season).
      2. Накладываем эффект для new_idx (_apply_season).
      3. Сохраняем last_idx = new_idx.

    Если new_idx == last_idx, ничего не делаем.
    """

    # Для удобства: названия сезонов (индексы 0–3)
    SEASON_NAMES = ['Зима', 'Весна', 'Лето', 'Осень']

    # Для каждого сезона (по индексу) храним словарь:
    #   ключ = название фракции,
    #   значение = { 'stat': коэффициент для attack/defense, 'cost': коэффициент для cost_money/cost_time }
    FACTION_EFFECTS = [
        # 0 = Зима
        {
            'Аркадия':  {'stat': 1.25,  'cost': 0.65},   # +25% атак/защита, -35% стоимости
            'Селестия': {'stat': 0.65,  'cost': 1.25},   # -35% атак/защита, +25% стоимости
            'Хиперион': {'stat': 0.97,  'cost': 1.00},   # -3% атак/защита, нет эффекта стоимости
            'Этерия':   {'stat': 0.90,  'cost': 1.17},   # -10% атак/защита, +17% стоимости
            'Халидон':  {'stat': 0.60,  'cost': 1.25},   # -40% атак/защита, +25% стоимости
        },
        # 1 = Весна
        {
            'Аркадия':  {'stat': 0.90,  'cost': 1.17},   # -10% атак/защита, +17% стоимости
            'Селестия': {'stat': 0.97,  'cost': 1.00},   # -3% атак/защита, нет эффекта стоимости
            'Хиперион': {'stat': 1.25,  'cost': 0.65},   # +25% атак/защита, -35% стоимости
            'Этерия':   {'stat': 0.65,  'cost': 1.25},   # -35% атак/защита, +25% стоимости
            'Халидон':  {'stat': 0.97,  'cost': 0.95},   # -3% атак/защита, -5% стоимости
        },
        # 2 = Лето
        {
            'Аркадия':  {'stat': 0.65,  'cost': 1.25},   # -35% атак/защита, +25% стоимости
            'Селестия': {'stat': 1.25,  'cost': 0.65},   # +25% атак/защита, -35% стоимости
            'Хиперион': {'stat': 0.90,  'cost': 1.17},   # -10% атак/защита, +17% стоимости
            'Этерия':   {'stat': 0.97,  'cost': 1.00},   # -3% атак/защита, нет эффекта стоимости
            'Халидон':  {'stat': 1.60,  'cost': 0.65},   # +60% атак/защита, -35% стоимости
        },
        # 3 = Осень
        {
            'Аркадия':  {'stat': 0.97,  'cost': 1.00},   # -3% атак/защита, нет эффекта стоимости
            'Селестия': {'stat': 0.90,  'cost': 1.17},   # -10% атак/защита, +17% стоимости
            'Хиперион': {'stat': 0.65,  'cost': 1.25},   # -35% атак/защита, +25% стоимости
            'Этерия':   {'stat': 1.25,  'cost': 0.65},   # +25% атак/защита, -35% стоимости
            'Халидон':  {'stat': 0.90,  'cost': 1.17},   # -10% атак/защита, +17% стоимости
        },
    ]

    def __init__(self):
        # last_idx = индекс сезона, бафф которого уже наложен.
        # None означает, что до этого ни один сезон не применялся.
        self.last_idx = None

    def update(self, new_idx: int, conn):
        """
        Вызывается при смене сезона на new_idx (0–3).
        Если last_idx != new_idx, то:
          1) Если last_idx не None, откатываем _revert_season(last_idx).
          2) Накладываем _apply_season(new_idx).
          3) Сохраняем last_idx = new_idx.
        Если new_idx == last_idx, ничего не делаем.
        """
        if self.last_idx is None:
            # Первый раз — просто накладываем
            self._apply_season(new_idx, conn)
            self.last_idx = new_idx
        elif new_idx != self.last_idx:
            # Сначала откатить предыдущий сезон
            self._revert_season(self.last_idx, conn)
            # Потом применить новый
            self._apply_season(new_idx, conn)
            self.last_idx = new_idx
        # Если new_idx == last_idx, остаёмся как есть

    def _apply_season(self, idx: int, conn):
        """
        Накладывает все эффекты сезона idx на таблицу units,
        по каждой фракции берутся соответствующие коэффициенты.
        """
        faction_effects = self.FACTION_EFFECTS[idx]
        cur = conn.cursor()

        for faction_name, coeffs in faction_effects.items():
            stat_f = coeffs['stat']
            cost_f = coeffs['cost']

            # Применяем stat-коэффициент (attack, defense) только если stat_f != 1.0
            if stat_f != 1.0:
                cur.execute(f"""
                    UPDATE units
                    SET
                        attack  = CAST(ROUND(attack  * :stat_f) AS INTEGER),
                        defense = CAST(ROUND(defense * :stat_f) AS INTEGER)
                    WHERE faction = :faction
                """, {'stat_f': stat_f, 'faction': faction_name})

            # Применяем cost-коэффициент (cost_money, cost_time) только если cost_f != 1.0
            if cost_f != 1.0:
                cur.execute(f"""
                    UPDATE units
                    SET
                        cost_money = CAST(ROUND(cost_money * :cost_f) AS INTEGER),
                        cost_time  = CAST(ROUND(cost_time  * :cost_f) AS INTEGER)
                    WHERE faction = :faction
                """, {'cost_f': cost_f, 'faction': faction_name})

        conn.commit()

    def _revert_season(self, idx: int, conn):
        """
        Откатывает эффекты сезона idx, возвращая к «базовым» значениям.
        Для каждой фракции берём обратные коэффициенты: 1 / applied_factor.
        """
        faction_effects = self.FACTION_EFFECTS[idx]
        cur = conn.cursor()

        for faction_name, coeffs in faction_effects.items():
            stat_f = coeffs['stat']
            cost_f = coeffs['cost']

            # Откатим stat, если он не равен 1.0
            if stat_f != 1.0:
                stat_revert = 1.0 / stat_f
                cur.execute(f"""
                    UPDATE units
                    SET
                        attack  = CAST(ROUND(attack  * :stat_rev) AS INTEGER),
                        defense = CAST(ROUND(defense * :stat_rev) AS INTEGER)
                    WHERE faction = :faction
                """, {'stat_rev': stat_revert, 'faction': faction_name})

            # Откатим cost, если он не равен 1.0
            if cost_f != 1.0:
                cost_revert = 1.0 / cost_f
                cur.execute(f"""
                    UPDATE units
                    SET
                        cost_money = CAST(ROUND(cost_money * :cost_rev) AS INTEGER),
                        cost_time  = CAST(ROUND(cost_time  * :cost_rev) AS INTEGER)
                    WHERE faction = :faction
                """, {'cost_rev': cost_revert, 'faction': faction_name})

        conn.commit()
