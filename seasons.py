# seasons.py
from db_lerdon_connect import *

class SeasonManager:
    """
    Упрощённый менеджер сезонов. Теперь НЕ СЧИТАЕТ turn_count из БД,
    а просто получает индекс сезона (0–3) извне и применяет бафф/дебафф
    к таблице units:

      0 = Зима   (стоимость +15%, характеристики ×1.00)
      1 = Весна  (стоимость ×1.00, характеристики ×0.96)
      2 = Лето   (стоимость ×1.00, характеристики ×1.03)
      3 = Осень  (стоимость ×1.00, характеристики ×0.91)

    При первом вызове update(new_idx) просто накладывается бафф/дебафф
    для текущей индексации. При смене индекса с last_idx на новый –
    сначала откатывается эффект last_idx, потом накладывается эффект new_idx.
    """

    # Факторы для каждого сезона (по индексу)
    SEASONS = [
        {
            'name': 'Зима',
            'cost_factor': 1.15,
            'stat_factor': 1.00
        },
        {
            'name': 'Весна',
            'cost_factor': 1.00,
            'stat_factor': 0.96
        },
        {
            'name': 'Лето',
            'cost_factor': 1.00,
            'stat_factor': 1.03
        },
        {
            'name': 'Осень',
            'cost_factor': 1.00,
            'stat_factor': 0.91
        },
    ]

    # Откат для стоимости (только для Зимы, индекс 0)
    COST_REVERT_FACTORS = [
        1 / 1.15,  # когда уходим из Зимы
        None,
        None,
        None
    ]

    # Откат для характеристик (attack/defense/durability) для всех сезонов, где stat_factor != 1.0
    REVERT_FACTORS = [
        None,            # у Зимы stat_factor 1.00 — отката не требуется
        1 / 0.96,        # у Весны stat_factor 0.96 — чтобы вернуть ×1.00, надо ×(1/0.96)
        1 / 1.03,        # у Лета stat_factor 1.03 — откат ×(1/1.03)
        1 / 0.91         # у Осени stat_factor 0.91 — откат ×(1/0.91)
    ]

    def __init__(self):
        # last_idx = индекс сезона, бафф которого уже наложен на units.
        # При старте — ничего не наложено, поэтому ставим None.
        self.last_idx = None

    def update(self, new_idx: int):
        """
        Вызывается из game_process.py, когда у вас меняется сезон на new_idx (0–3).
        Если last_idx != new_idx, то:
          1. Если last_idx не None, откатываем эффект last_idx (_revert_season).
          2. Применяем эффект new_idx (_apply_season).
          3. Запоминаем last_idx = new_idx.

        Если new_idx == last_idx, ничего не делаем.
        """
        # Если это первый вызов (last_idx None) или просто смена индекса
        if self.last_idx is None:
            # Просто накладываем эффект нового сезона, отката нет
            self._apply_season(new_idx)
            self.last_idx = new_idx

        elif new_idx != self.last_idx:
            # Сначала откатить предыдущий
            self._revert_season(self.last_idx)
            # Теперь применить новый
            self._apply_season(new_idx)
            self.last_idx = new_idx


    def _apply_season(self, idx: int):
        """
        Реально «накладывает» бафф или дебафф для сезона с индексом idx,
        корректируя таблицу units:
          - cost_money, cost_time (при cost_factor != 1.0)
          - attack, defense, durability (при stat_factor != 1.0)
        """
        season = self.SEASONS[idx]
        cost_f = season['cost_factor']
        stat_f = season['stat_factor']

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Если cost_factor <> 1.0, применяем на cost_money и cost_time
        if cost_f != 1.0:
            cur.execute("""
                UPDATE units
                SET
                    cost_money = CAST(ROUND(cost_money * ?) AS INTEGER),
                    cost_time  = CAST(ROUND(cost_time  * ?) AS INTEGER)
            """, (cost_f, cost_f))

        # Если stat_factor <> 1.0, применяем на attack, defense, durability
        if stat_f != 1.0:
            cur.execute("""
                UPDATE units
                SET
                    attack     = CAST(ROUND(attack     * ?) AS INTEGER),
                    defense    = CAST(ROUND(defense    * ?) AS INTEGER),
                    durability = CAST(ROUND(durability * ?) AS INTEGER)
            """, (stat_f, stat_f, stat_f))

        conn.commit()
        conn.close()

    def _revert_season(self, idx: int):
        """
        Откатывает эффекты сезона с индексом idx, возвращая «прошлые» значения к базовому.
        """
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 1) Откат стоимости (cost_money, cost_time) — только для idx == 0 (Зима)
        cost_revert = self.COST_REVERT_FACTORS[idx]
        if cost_revert is not None:
            cur.execute("""
                UPDATE units
                SET
                    cost_money = CAST(ROUND(cost_money * ?) AS INTEGER),
                    cost_time  = CAST(ROUND(cost_time  * ?) AS INTEGER)
            """, (cost_revert, cost_revert))

        # 2) Откат характеристик (attack, defense, durability) — если stat_factor != 1.0
        stat_revert = self.REVERT_FACTORS[idx]
        if stat_revert is not None:
            cur.execute("""
                UPDATE units
                SET
                    attack     = CAST(ROUND(attack     * ?) AS INTEGER),
                    defense    = CAST(ROUND(defense    * ?) AS INTEGER),
                    durability = CAST(ROUND(durability * ?) AS INTEGER)
            """, (stat_revert, stat_revert, stat_revert))

        conn.commit()
        conn.close()
