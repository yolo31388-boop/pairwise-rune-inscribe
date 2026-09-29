"""技能符文与铭刻系统"""
import random
from dataclasses import dataclass, field

SLOT_TYPES = ("red", "blue", "green")
ADVANCED_LEVEL = 10
SAME_TYPE_LIMIT = 3
SET_PIECE_REQUIRED = 3
SET_BONUS_ATK = 50
COMBINE_PITY_FAILURES = 3
MIN_COMBINE_RATE = 0.2

ADVANCED_UNIQUE_EFFECTS = {
    "red": ("烈焰焚天", {"crit_dmg": 0.30, "bonus_dmg": 0.10}),
    "blue": ("霜息涌动", {"cooldown_reduce": 0.20, "mana_regen": 0.15}),
    "green": ("荒野祝福", {"lifesteal": 0.15, "healing_bonus": 0.20}),
}


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
        self.equipment_slots: dict[str, dict[str, list]] = {}
        self.inscriptions: dict[str, list] = {}
        self._combine_fail_streak = 0

    def can_insert(self, rune: Rune, slot_type: str) -> bool:
        return rune.slot_type == slot_type

    def insert_rune(self, equip_id: str, slot_type: str, rune: Rune) -> tuple[bool, str]:
        if not self.can_insert(rune, slot_type):
            return False, "slot_type_mismatch"
        equip = self.equipment_slots.setdefault(equip_id, {})
        slot = equip.setdefault(slot_type, [])
        same_type = sum(1 for r in slot if r.name == rune.name)
        if same_type >= self.get_same_type_limit():
            return False, "same_type_limit"
        slot.append(rune)
        return True, "ok"

    def roll_stats(self, level: int) -> dict:
        base = level * 10
        factor = self.rng.uniform(0.85, 1.15)
        return {"atk": max(1, int(round(base * factor)))}

    def quality_grade(self, level: int, atk: int) -> str:
        base = level * 10
        if atk >= int(base * 1.1):
            return "perfect"
        if atk <= int(base * 0.9):
            return "poor"
        return "normal"

    def check_set_bonus(self, runes: list[Rune]) -> dict:
        groups: dict[str, list[Rune]] = {}
        for rune in runes:
            if not rune.set_id:
                continue
            groups.setdefault(rune.set_id, []).append(rune)
        bonus = {}
        for members in groups.values():
            if len(members) >= SET_PIECE_REQUIRED:
                bonus["atk"] = bonus.get("atk", 0) + SET_BONUS_ATK
        return bonus

    def inscribe(self, equip_id: str, effect: dict) -> None:
        self.inscriptions.setdefault(equip_id, []).append(effect)

    def is_inscribe_bound(self, equip_id: str) -> bool:
        return True

    def active_inscribe_effects(self, worn_equip_ids: list[str]) -> list:
        effects = []
        for equip_id in worn_equip_ids:
            effects.extend(self.inscriptions.get(equip_id, []))
        return effects

    def get_advanced_effect(self, rune: Rune) -> dict:
        if rune.level < ADVANCED_LEVEL:
            return {}
        unique_name, base_effect = ADVANCED_UNIQUE_EFFECTS.get(
            rune.slot_type, ("全能觉醒", {"all_stats": 0.10})
        )
        scale = 1 + (rune.level - ADVANCED_LEVEL) * 0.1
        effect = {"unique": unique_name}
        for key, value in base_effect.items():
            effect[key] = round(value * scale, 3)
        return effect

    def get_same_type_limit(self) -> int:
        return SAME_TYPE_LIMIT

    def combine_rate(self, target_level: int) -> float:
        return max(MIN_COMBINE_RATE, 1.0 - target_level * 0.05)

    def combine(self, runes: list[Rune]) -> tuple[Rune | None, str]:
        if len(runes) < 3:
            return None, "need 3"
        base = runes[0]
        target_level = base.level + 1
        guaranteed = self._combine_fail_streak >= COMBINE_PITY_FAILURES
        if not guaranteed and self.rng.random() > self.combine_rate(target_level):
            self._combine_fail_streak += 1
            return None, "combine_failed"
        self._combine_fail_streak = 0
        return Rune(
            f"r{self.rng.randint(1000, 9999)}",
            base.name,
            target_level,
            base.slot_type,
            set_id=base.set_id,
            stats=self.roll_stats(target_level),
        ), "success"
