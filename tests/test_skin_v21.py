"""Unit tests for Skin Analysis v2.1 (no API calls)."""

import pytest

from perfectcorp.apis.skin_v21 import (
    HD_ACTIONS,
    SD_ACTIONS,
    _validate_dst_actions,
)


def test_hd_actions_count():
    assert len(HD_ACTIONS) == 16


def test_sd_actions_count():
    assert len(SD_ACTIONS) == 16


def test_validate_all_hd():
    _validate_dst_actions(HD_ACTIONS)  # must not raise


def test_validate_all_sd():
    _validate_dst_actions(SD_ACTIONS)  # must not raise


def test_validate_subset_hd():
    _validate_dst_actions(["hd_acne", "hd_pore", "hd_wrinkle"])


def test_validate_subset_sd():
    _validate_dst_actions(["acne", "pore", "wrinkle"])


def test_validate_mixed_raises():
    with pytest.raises(ValueError, match="cannot be mixed"):
        _validate_dst_actions(["hd_acne", "acne"])


def test_validate_unknown_raises():
    with pytest.raises(ValueError, match="Unknown dst_actions"):
        _validate_dst_actions(["hd_acne", "nonexistent_feature"])


def test_hd_no_duplicates():
    assert len(HD_ACTIONS) == len(set(HD_ACTIONS))


def test_sd_no_duplicates():
    assert len(SD_ACTIONS) == len(set(SD_ACTIONS))


def test_hd_sd_no_overlap():
    assert not (set(HD_ACTIONS) & set(SD_ACTIONS))
