"""Tests de fumée — le squelette s'importe et les invariants de base tiennent."""

from ninja_cat import __version__
from ninja_cat.config import DEFAULT_CONFIG, Config
from ninja_cat.schema import Bar, Side, Trade


def test_version():
    assert isinstance(__version__, str)


def test_config_defaults_scale_free():
    c = Config()
    assert c.imbalance_ratio == 3.0
    assert c.sequence_min_levels >= 4
    assert 0.0 < c.poc_bottom_threshold < c.poc_top_threshold < 1.0
    assert DEFAULT_CONFIG == c


def test_trade_signed_size_convention():
    assert Trade(ts=0, price=100.0, size=2.0, side=Side.BUY).signed_size == 2.0
    assert Trade(ts=0, price=100.0, size=2.0, side=Side.SELL).signed_size == -2.0


def test_bar_construction():
    bar = Bar(
        ts_open=0, ts_close=1000,
        open=100.0, high=101.0, low=99.0, close=100.5,
        volume=10.0, delta=-3.0, delta_max=2.0, delta_min=-5.0,
        poc_price=99.5, poc_position=0.25,
        levels={99.5: (4.0, 1.0), 100.5: (1.0, 4.0)},
    )
    assert bar.low <= bar.poc_price <= bar.high
    assert 0.0 <= bar.poc_position <= 1.0
