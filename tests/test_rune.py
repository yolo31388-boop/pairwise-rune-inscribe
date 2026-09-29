"""技能符文与铭刻系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rune.inscribe import RuneSystem, Rune

class TestSlotType:
    def test_red_rune_cannot_go_blue_slot(self):
        rs = RuneSystem()
        rune = Rune("r1", "fire", 5, "red")
        assert rs.can_insert(rune, "blue") == False
        assert rs.can_insert(rune, "red") == True

class TestStatsVariance:
    def test_same_level_runes_have_variance(self):
        rs = RuneSystem(seed=42)
        stats_list = [rs.roll_stats(5) for _ in range(20)]
        values = [s["atk"] for s in stats_list]
        assert len(set(values)) > 1

class TestSetBonus:
    def test_mixed_sets_dont_trigger_3piece(self):
        rs = RuneSystem()
        runes = [Rune(f"r{i}", "x", 5, "red", set_id=s) for i, s in enumerate(["A", "A", "B"])]
        result = rs.check_set_bonus(runes)
        assert result == {} or result.get("atk", 0) < 50

class TestInscribeBound:
    def test_inscribe_effect_bound_to_equip(self):
        rs = RuneSystem()
        assert rs.is_inscribe_bound("e1") == True

class TestAdvancedEffect:
    def test_high_level_rune_has_unique_effect(self):
        rs = RuneSystem()
        rune = Rune("r1", "fire", 10, "red")
        assert rs.get_advanced_effect(rune) != {}

class TestSameTypeLimit:
    def test_same_type_rune_has_limit(self):
        rs = RuneSystem()
        assert rs.get_same_type_limit() < 5

class TestCombineFailure:
    def test_combine_can_fail(self):
        rs = RuneSystem(seed=1)
        runes = [Rune(f"r{i}", "fire", 8, "red") for i in range(3)]
        results = [rs.combine(runes) for _ in range(20)]
        success = sum(1 for r, _ in results if r)
        assert success < 20
