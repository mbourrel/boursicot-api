"""
Tests d'intégration — endpoints critiques :
  - GET /api/screener
  - GET /api/assets
"""
import pytest
from models import Company
from assets_config import ASSET_DICTIONARY


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stock(ticker="AAPL", sector="Technology"):
    return Company(
        ticker=ticker,
        name="Apple Inc.",
        sector=sector,
        asset_class="stock",
        country="United States",
        live_price=175.50,
        live_change_pct=1.23,
        scores_json={
            "health": 7.5, "valuation": 6.0, "growth": 8.0,
            "dividend": 3.0, "momentum": 7.0, "efficiency": 7.5,
            "global_score": 6.8, "verdict": "Solide",
        },
    )


def _non_scorable(ticker="BTC-USD"):
    return Company(
        ticker=ticker,
        name="Bitcoin",
        sector=None,
        asset_class="crypto",
        country=None,
        live_price=65000.0,
        live_change_pct=-0.5,
        scores_json=None,
    )


# ── GET /api/screener ─────────────────────────────────────────────────────────

class TestScreener:

    def test_empty_db_returns_empty_list(self, client):
        r = client.get("/api/screener")
        assert r.status_code == 200
        assert r.json() == []

    def test_stock_appears_in_response(self, client, db):
        db.add(_stock())
        db.commit()

        items = client.get("/api/screener").json()
        assert len(items) == 1
        assert items[0]["ticker"] == "AAPL"
        assert items[0]["name"] == "Apple Inc."
        assert items[0]["sector"] == "Technology"

    def test_scorable_stock_exposes_scores(self, client, db):
        db.add(_stock())
        db.commit()

        item = client.get("/api/screener").json()[0]
        assert item["is_scorable"] is True
        assert item["scores"] is not None
        assert "global_score" in item["scores"]
        assert item["scores"]["global_score"] == pytest.approx(6.8)

    def test_non_scorable_crypto_has_null_scores(self, client, db):
        db.add(_non_scorable("BTC-USD"))
        db.commit()

        item = client.get("/api/screener").json()[0]
        assert item["is_scorable"] is False
        assert item["scores"] is None

    def test_response_fields_complete(self, client, db):
        db.add(_stock())
        db.commit()

        item = client.get("/api/screener").json()[0]
        expected = {
            "ticker", "name", "sector", "country", "asset_class",
            "is_scorable", "scores", "live_price", "live_change_pct",
        }
        assert set(item.keys()) == expected

    def test_live_price_and_change_returned(self, client, db):
        db.add(_stock())
        db.commit()

        item = client.get("/api/screener").json()[0]
        assert item["live_price"] == pytest.approx(175.50)
        assert item["live_change_pct"] == pytest.approx(1.23)

    def test_multiple_companies_all_returned(self, client, db):
        db.add(_stock("AAPL", "Technology"))
        db.add(_stock("MSFT", "Technology"))
        db.add(_non_scorable("BTC-USD"))
        db.commit()

        items = client.get("/api/screener").json()
        assert len(items) == 3
        tickers = {i["ticker"] for i in items}
        assert tickers == {"AAPL", "MSFT", "BTC-USD"}

    @pytest.mark.parametrize("ticker", ["^FCHI", "^GSPC", "GC=F", "ZW=F"])
    def test_index_and_commodity_are_non_scorable(self, client, db, ticker):
        db.add(Company(ticker=ticker, name="Test Asset", asset_class="index"))
        db.commit()

        item = client.get("/api/screener").json()[0]
        assert item["is_scorable"] is False
        assert item["scores"] is None

    def test_country_field_propagated(self, client, db):
        db.add(_stock())
        db.commit()

        item = client.get("/api/screener").json()[0]
        assert item["country"] == "United States"

    def test_asset_class_field_propagated(self, client, db):
        db.add(_non_scorable("ETH-USD"))
        db.commit()

        item = client.get("/api/screener").json()[0]
        assert item["asset_class"] == "crypto"


# ── GET /api/assets ───────────────────────────────────────────────────────────

class TestAssets:

    def test_returns_all_catalog_tickers(self, client):
        r = client.get("/api/assets")
        assert r.status_code == 200
        returned = {i["ticker"] for i in r.json()}
        assert returned == set(ASSET_DICTIONARY.keys())

    def test_response_count_matches_catalog(self, client):
        items = client.get("/api/assets").json()
        assert len(items) == len(ASSET_DICTIONARY)

    def test_each_item_has_required_fields(self, client):
        for item in client.get("/api/assets").json():
            assert "ticker" in item
            assert "name" in item
            assert "country" in item
            assert "sector" in item
            assert "asset_class" in item

    def test_names_come_from_catalog(self, client):
        item_map = {i["ticker"]: i for i in client.get("/api/assets").json()}
        assert item_map["AAPL"]["name"] == "Apple"
        assert item_map["BTC-USD"]["name"] == "Bitcoin"
        assert item_map["^FCHI"]["name"] == "CAC 40"
        assert item_map["CW8.PA"]["name"] == "Amundi MSCI World"

    def test_db_enrichment_fills_sector_country_asset_class(self, client, db):
        db.add(Company(
            ticker="AAPL",
            name="Apple Inc.",
            sector="Technology",
            asset_class="stock",
            country="United States",
        ))
        db.commit()

        item_map = {i["ticker"]: i for i in client.get("/api/assets").json()}
        aapl = item_map["AAPL"]
        assert aapl["sector"] == "Technology"
        assert aapl["country"] == "United States"
        assert aapl["asset_class"] == "stock"

    def test_ticker_absent_from_db_returns_none_fields(self, client):
        # Sans Company en DB, les champs enrichis sont None
        item_map = {i["ticker"]: i for i in client.get("/api/assets").json()}
        aapl = item_map["AAPL"]
        assert aapl["country"] is None
        assert aapl["sector"] is None
        assert aapl["asset_class"] is None

    def test_partial_db_coverage_no_error(self, client, db):
        # Seulement quelques tickers en DB — les autres renvoient None proprement
        db.add(Company(ticker="AAPL", name="Apple", sector="Technology", asset_class="stock"))
        db.add(Company(ticker="MC.PA", name="LVMH", sector="Consumer Cyclical", asset_class="stock"))
        db.commit()

        items = client.get("/api/assets").json()
        assert len(items) == len(ASSET_DICTIONARY)
        item_map = {i["ticker"]: i for i in items}
        assert item_map["AAPL"]["sector"] == "Technology"
        assert item_map["MSFT"]["sector"] is None  # absent de la DB
