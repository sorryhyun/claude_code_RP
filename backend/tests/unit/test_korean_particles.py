"""
Unit tests for Korean particle utility functions.

Tests the automatic selection of Korean particles (조사) based on
whether a word ends with a consonant (받침) or vowel.
"""

import pytest
from i18n.korean import format_with_particles, has_final_consonant


class TestHasFinalConsonant:
    """Tests for has_final_consonant function."""

    @pytest.mark.unit
    def test_consonant_ending(self):
        """Test words ending with consonant (받침)."""
        assert has_final_consonant("프리렌") is True  # 'ㄴ' final consonant
        assert has_final_consonant("전지맨") is True  # 'ㄴ' final consonant
        assert has_final_consonant("힘멜") is True  # 'ㄹ' final consonant
        assert has_final_consonant("막") is True  # 'ㄱ' final consonant

    @pytest.mark.unit
    def test_vowel_ending(self):
        """Test words ending with vowel (no 받침)."""
        assert has_final_consonant("히메") is False  # No final consonant
        assert has_final_consonant("파워") is False  # No final consonant
        assert has_final_consonant("치즈루") is False  # No final consonant
        assert has_final_consonant("마키마") is False  # No final consonant

    @pytest.mark.unit
    def test_empty_string(self):
        """Test empty string returns False."""
        assert has_final_consonant("") is False

    @pytest.mark.unit
    def test_non_korean_characters(self):
        """Test non-Korean characters default to consonant ending."""
        # English, numbers, etc. default to True for safer grammar
        assert has_final_consonant("Alice") is True
        assert has_final_consonant("123") is True
        assert has_final_consonant("Test") is True

    @pytest.mark.unit
    def test_mixed_text(self):
        """Test mixed Korean/non-Korean text uses last character."""
        assert has_final_consonant("Alice프리렌") is True  # Last char: 렌 (has 받침)
        assert has_final_consonant("Test히메") is False  # Last char: 메 (no 받침)
        assert has_final_consonant("데nji") is True  # Last char: i (English defaults to True)


class TestFormatWithParticles:
    """Tests for format_with_particles function."""

    @pytest.mark.unit
    def test_subject_particle_consonant(self):
        """Test 이/가 particle with consonant ending."""
        result = format_with_particles("{name:이가} 말했다", name="프리렌")
        assert result == "프리렌이 말했다"

        result = format_with_particles("{name:이가} 강하다", name="막")
        assert result == "막이 강하다"  # 막 ends with ㄱ final consonant

    @pytest.mark.unit
    def test_subject_particle_vowel(self):
        """Test 이/가 particle with vowel ending."""
        result = format_with_particles("{name:이가} 말했다", name="히메")
        assert result == "히메가 말했다"

        result = format_with_particles("{name:이가} 웃었다", name="파워")
        assert result == "파워가 웃었다"

    @pytest.mark.unit
    def test_topic_particle_consonant(self):
        """Test 은/는 particle with consonant ending."""
        result = format_with_particles("{name:은는} 강하다", name="프리렌")
        assert result == "프리렌은 강하다"

    @pytest.mark.unit
    def test_topic_particle_vowel(self):
        """Test 은/는 particle with vowel ending."""
        result = format_with_particles("{name:은는} 귀엽다", name="히메")
        assert result == "히메는 귀엽다"

    @pytest.mark.unit
    def test_object_particle_consonant(self):
        """Test 을/를 particle with consonant ending."""
        result = format_with_particles("{name:을를} 좋아한다", name="전지맨")
        assert result == "전지맨을 좋아한다"

    @pytest.mark.unit
    def test_object_particle_vowel(self):
        """Test 을/를 particle with vowel ending."""
        result = format_with_particles("{name:을를} 좋아한다", name="치즈루")
        assert result == "치즈루를 좋아한다"

    @pytest.mark.unit
    def test_conjunction_particle_consonant(self):
        """Test 과/와 particle with consonant ending."""
        result = format_with_particles("{name1:과와} {name2}", name1="프리렌", name2="히메")
        assert result == "프리렌과 히메"

    @pytest.mark.unit
    def test_conjunction_particle_vowel(self):
        """Test 과/와 particle with vowel ending."""
        result = format_with_particles("{name1:과와} {name2}", name1="히메", name2="프리렌")
        assert result == "히메와 프리렌"

    @pytest.mark.unit
    def test_direction_particle_consonant(self):
        """Test 으로/로 particle with consonant ending."""
        result = format_with_particles("{name:으로로}서", name="프리렌")
        assert result == "프리렌으로서"

    @pytest.mark.unit
    def test_direction_particle_vowel(self):
        """Test 으로/로 particle with vowel ending."""
        result = format_with_particles("{name:으로로}서", name="치즈루")
        assert result == "치즈루로서"

    @pytest.mark.unit
    def test_multiple_particles(self):
        """Test multiple particles in one template."""
        template = "{name1:이가} {name2:을를} 만났다. {name1:은는} {name2:과와} 친구다."
        result = format_with_particles(template, name1="프리렌", name2="히메")
        assert result == "프리렌이 히메를 만났다. 프리렌은 히메와 친구다."

    @pytest.mark.unit
    def test_simple_placeholder(self):
        """Test simple placeholder without particles."""
        result = format_with_particles("안녕하세요, {name}님!", name="프리렌")
        assert result == "안녕하세요, 프리렌님!"

    @pytest.mark.unit
    def test_mixed_placeholders(self):
        """Test mixing particle and simple placeholders."""
        result = format_with_particles("{name:이가} {greeting}!", name="히메", greeting="안녕")
        assert result == "히메가 안녕!"

    @pytest.mark.unit
    def test_no_placeholders(self):
        """Test template with no placeholders."""
        result = format_with_particles("이것은 테스트입니다")
        assert result == "이것은 테스트입니다"

    @pytest.mark.unit
    def test_english_names(self):
        """Test English names (default to consonant ending)."""
        result = format_with_particles("{name:이가} 말했다", name="Alice")
        assert result == "Alice이 말했다"

        result = format_with_particles("{name:은는} 강하다", name="Bob")
        assert result == "Bob은 강하다"
