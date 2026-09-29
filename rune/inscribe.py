"""技能符文与铭刻系统 - 含7个bug"""
import random
from dataclasses import dataclass, field

@dataclass
class Rune:
    rid: str
    name: str
    level: int
    slot_type: str  # red/blue/green
    set_id: str = ""
    stats: dict = field(default_factory=dict)

class RuneSystem:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.equipment_slots: dict[str, list] = {}

    def can_insert(self, rune: Rune, slot_type: str) -> bool:
        # bug1: 不检查槽位类型
        return True

    def roll_stats(self, level: int) -> dict:
        # bug2: 固定值无浮动
        return {"atk": level * 10}

    def check_set_bonus(self, runes: list[Rune]) -> dict:
        # bug3: 不按set_id分组
        if len(runes) >= 3:
            return {"atk": 50}
        return {}

    def is_inscribe_bound(self, equip_id: str) -> bool:
        # bug4: 铭刻效果全局
        return False

    def get_advanced_effect(self, rune: Rune) -> dict:
        # bug5: 高级符文无专属
        return {}

    def get_same_type_limit(self) -> int:
        # bug6: 无数量限制
        return 999

    def combine(self, runes: list[Rune]) -> tuple[Rune | None, str]:
        # bug7: 100%成功
        if len(runes) < 3:
            return None, "need 3"
        return Rune(f"r{self.rng.randint(1000,9999)}", runes[0].name, runes[0].level + 1, runes[0].slot_type), "success"
