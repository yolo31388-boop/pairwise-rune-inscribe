"""技能符文与铭刻系统"""
import random
from dataclasses import dataclass, field

SLOT_TYPES = ("red", "blue", "green")

# 品质 -> (权重, 最小倍率, 最大倍率, 中文名)
QUALITY_TABLE = {
    "inferior": (10, 0.70, 0.85, "次品"),
    "common":   (45, 0.85, 1.00, "普通"),
    "fine":     (30, 1.00, 1.15, "优秀"),
    "epic":     (15, 1.15, 1.30, "极品"),
}
QUALITY_NAMES = {k: v[3] for k, v in QUALITY_TABLE.items()}

ADVANCED_LEVEL = 10

# 高级符文按槽位颜色拥有的专属词条
ADVANCED_AFFIX = {
    "red":   {"crit_rate": 0.15, "crit_dmg": 0.50},
    "blue":  {"cooldown_reduce": 0.20, "skill_amp": 0.25},
    "green": {"lifesteal": 0.10, "heal_bonus": 0.20},
}

# 同套装件数 -> 套装效果（必须同一 set_id）
SET_BONUSES = {
    3: {"atk": 50},
    6: {"atk": 120, "crit_rate": 0.20},
}

SAME_TYPE_LIMIT = 3       # 一件装备同类符文最多生效数量
MISMATCH_FACTOR = 0.5     # 异色槽强行镶嵌时的效果衰减
PITY_FAILS = 5            # 连续失败保底次数


@dataclass
class Rune:
    rid: str
    name: str
    level: int
    slot_type: str  # red/blue/green
    set_id: str = ""
    stats: dict = field(default_factory=dict)
    quality: str = "common"
    exclusive_affix: dict = field(default_factory=dict)


class RuneSystem:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        # equip_id -> 该装备各槽位的颜色
        self.equipment_slots: dict[str, list[str]] = {}
        # equip_id -> 已镶嵌符文（与槽位等长，空位为 None）
        self.socketed: dict[str, list] = {}
        # equip_id -> 铭刻效果（绑定装备，非全局）
        self.inscriptions: dict[str, dict] = {}
        self.combine_streak = 0  # 连续合成失败计数（保底）

    # ---- bug1: 槽位颜色/类型限制 ----
    def can_insert(self, rune: Rune, slot_type: str) -> bool:
        if slot_type == "any":
            return rune.slot_type in SLOT_TYPES
        return rune.slot_type == slot_type

    def slot_effect_multiplier(self, rune: Rune, slot_type: str) -> float:
        return 1.0 if self.can_insert(rune, slot_type) else MISMATCH_FACTOR

    def configure_equipment(self, equip_id: str, slot_types: list[str]):
        self.equipment_slots[equip_id] = list(slot_types)
        self.socketed[equip_id] = [None] * len(slot_types)

    def insert_rune(self, equip_id: str, slot_index: int, rune: Rune) -> str:
        slots = self.equipment_slots.get(equip_id)
        if slots is None:
            return "equipment not configured"
        if not (0 <= slot_index < len(slots)):
            return "invalid slot"
        if not self.can_insert(rune, slots[slot_index]):
            return "slot type mismatch"
        placed = [r for r in self.socketed[equip_id] if r is not None]
        same_type = sum(1 for r in placed if r.name == rune.name)
        if same_type >= self.get_same_type_limit():
            return "same type limit reached"
        self.socketed[equip_id][slot_index] = rune
        return "success"

    # ---- bug2: 属性在基础值上下浮动，区分极品/次品 ----
    def roll_quality(self) -> str:
        total = sum(v[0] for v in QUALITY_TABLE.values())
        pick = self.rng.uniform(0, total)
        upto = 0
        for quality, (weight, _, _, _) in QUALITY_TABLE.items():
            upto += weight
            if pick <= upto:
                return quality
        return "common"

    def roll_stats(self, level: int, quality: str | None = None) -> dict:
        quality = quality or self.roll_quality()
        _, lo, hi, _ = QUALITY_TABLE[quality]
        multiplier = self.rng.uniform(lo, hi)
        return {"atk": max(1, round(level * 10 * multiplier))}

    def craft_rune(self, rid: str, name: str, level: int,
                   slot_type: str, set_id: str = "") -> Rune:
        quality = self.roll_quality()
        rune = Rune(rid, name, level, slot_type, set_id,
                    stats=self.roll_stats(level, quality), quality=quality)
        rune.exclusive_affix = self.get_advanced_effect(rune)
        return rune

    # ---- bug3: 套装效果按 set_id 分组，同组达到件数才触发 ----
    def check_set_bonus(self, runes: list[Rune]) -> dict:
        counts: dict[str, int] = {}
        for rune in runes:
            if rune.set_id:
                counts[rune.set_id] = counts.get(rune.set_id, 0) + 1
        bonus: dict = {}
        for count in counts.values():
            reached = max((need for need in SET_BONUSES if need <= count), default=None)
            if reached is not None:
                for key, value in SET_BONUSES[reached].items():
                    bonus[key] = bonus.get(key, 0) + value
        return bonus

    # ---- bug4: 铭刻效果绑定装备，只在穿戴该装备时生效 ----
    def inscribe(self, equip_id: str, effect: dict):
        stored = self.inscriptions.setdefault(equip_id, {})
        for key, value in effect.items():
            stored[key] = stored.get(key, 0) + value

    def is_inscribe_bound(self, equip_id: str) -> bool:
        return bool(equip_id)

    def get_inscribe_effect(self, equip_id: str) -> dict:
        return dict(self.inscriptions.get(equip_id, {}))

    def active_inscribe_effects(self, equipped_ids: set[str]) -> dict:
        active: dict = {}
        for equip_id in equipped_ids:
            for key, value in self.inscriptions.get(equip_id, {}).items():
                active[key] = active.get(key, 0) + value
        return active

    # ---- bug5: 高级符文拥有专属词条 ----
    def get_advanced_effect(self, rune: Rune) -> dict:
        if rune.level < ADVANCED_LEVEL:
            return {}
        base = ADVANCED_AFFIX.get(rune.slot_type, {"all_damage": 0.20})
        scale = 1 + (rune.level - ADVANCED_LEVEL) * 0.1
        return {key: round(value * scale, 3) for key, value in base.items()}

    # ---- bug6: 同类符文有数量上限，超出部分不叠加 ----
    def get_same_type_limit(self) -> int:
        return SAME_TYPE_LIMIT

    def effective_runes(self, runes: list[Rune]) -> list[Rune]:
        seen: dict[str, int] = {}
        result = []
        for rune in runes:
            count = seen.get(rune.name, 0)
            if count < SAME_TYPE_LIMIT:
                result.append(rune)
                seen[rune.name] = count + 1
        return result

    def sum_rune_stats(self, runes: list[Rune]) -> dict:
        total: dict = {}
        for rune in self.effective_runes(runes):
            for key, value in rune.stats.items():
                total[key] = total.get(key, 0) + value
            for key, value in rune.exclusive_affix.items():
                total[key] = total.get(key, 0) + value
        return total

    # ---- bug7: 合成有成功率，等级越高越低，连续失败有保底 ----
    def combine_success_rate(self, target_level: int) -> float:
        return max(0.20, 0.90 - target_level * 0.05)

    def combine(self, runes: list[Rune]) -> tuple[Rune | None, str]:
        if len(runes) < 3:
            return None, "need 3 runes"
        base = runes[0]
        if any(r.level != base.level or r.slot_type != base.slot_type
               or r.name != base.name for r in runes):
            return None, "materials must be same type and level"
        target_level = base.level + 1
        guaranteed = self.combine_streak + 1 >= PITY_FAILS
        if guaranteed or self.rng.random() < self.combine_success_rate(target_level):
            self.combine_streak = 0
            rune = self.craft_rune(
                f"r{self.rng.randint(1000, 9999)}", base.name,
                target_level, base.slot_type, base.set_id,
            )
            return rune, "success"
        self.combine_streak += 1
        return None, f"combine failed ({self.combine_streak}/{PITY_FAILS})"
