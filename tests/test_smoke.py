"""Tests de fumée — le squelette s'importe et les invariants de base tiennent."""

from ninja_cat import __version__
from ninja_cat.config import DEFAULT_CONFIG, Config
from ninja_cat.schema import Side, Trade


def test_version():
    assert isinstance(__version__, str)


def test_config_defaults():
    c = Config()
    assert c.tick_size > 0.0
    assert DEFAULT_CONFIG == c


def test_trade_signed_size_convention():
    assert Trade(ts=0, price=100.0, size=2.0, side=Side.BUY).signed_size == 2.0
    assert Trade(ts=0, price=100.0, size=2.0, side=Side.SELL).signed_size == -2.0
