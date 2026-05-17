"""Tests for platform adapter identification logic."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from platforms.wordpress import WordPressAdapter
from platforms.squarespace import SquarespaceAdapter
from platforms.generic import GenericAdapter


WP_HTML = '<meta name="generator" content="WordPress 6.4" />'
SS_HTML = 'var SQUARESPACE_LOGIN_URL = "/config";Squarespace.afterBodyLoad(Y);'
GENERIC_HTML = "<html><body><p>Just a blog</p></body></html>"


def test_wordpress_identifies_generator_tag():
    adapter = WordPressAdapter()
    assert adapter.identify("https://example.com/post", WP_HTML)


def test_wordpress_identifies_wp_content():
    adapter = WordPressAdapter()
    assert adapter.identify("https://example.com/post", "/wp-content/themes/")


def test_squarespace_identifies_by_html():
    adapter = SquarespaceAdapter()
    assert adapter.identify("https://example.com/post", SS_HTML)


def test_squarespace_identifies_by_url():
    adapter = SquarespaceAdapter()
    assert adapter.identify("https://mysite.squarespace.com/post", "")


def test_generic_always_matches():
    adapter = GenericAdapter()
    assert adapter.identify("https://anything.com/post", "random html")
    assert adapter.identify("", "")


def test_wordpress_does_not_match_squarespace():
    adapter = WordPressAdapter()
    assert not adapter.identify("https://example.com/post", SS_HTML)
