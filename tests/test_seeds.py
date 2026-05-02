"""
Tests de la logique métier des scripts de seed.

Aucun appel réseau réel :
  - yfinance mocké via unittest.mock.patch
  - FMP (httpx) mocké via unittest.mock.patch
  - SessionLocal remplacée par TestSessionLocal (SQLite in-memory)
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from models import Company


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_price_history(n: int, start: float = 100.0) -> pd.DataFrame:
    """DataFrame de clôtures journalières sur n jours."""
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    closes = [start + i * 0.5 for i in range(n)]
    return pd.DataFrame({"Close": closes}, index=dates)


def _mock_yf_ticker(info: dict | None = None) -> MagicMock:
    """Mock yfinance.Ticker avec des fondamentaux Apple réalistes."""
    m = MagicMock()
    m.info = info or {
        "shortName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "longBusinessSummary": "Apple Inc. designs smartphones.",
        "country": "United States",
        "city": "Cupertino",
        "website": "https://www.apple.com",
        "fullTimeEmployees": 164000,
        "exchange": "NMS",
        "currency": "USD",
        "ipoDate": "1980-12-12",
        "quoteType": "EQUITY",
        "marketCap": 2_800_000_000_000,
        "trailingPE": 28.5,
        "dividendYield": 0.005,
        "profitMargins": 0.25,
        "returnOnEquity": 1.60,
        "debtToEquity": 150.0,
        "forwardPE": 26.0,
        "priceToBook": 45.0,
        "enterpriseToEbitda": 20.0,
        "pegRatio": 2.5,
        "totalRevenue": 394_000_000_000,
        "ebitda": 130_000_000_000,
        "revenueGrowth": 0.08,
        "earningsGrowth": 0.10,
        "totalCash": 60_000_000_000,
        "freeCashflow": 90_000_000_000,
        "currentRatio": 1.07,
        "beta": 1.24,
        "fiftyTwoWeekHigh": 198.0,
        "fiftyTwoWeekLow": 124.0,
        "shortPercentOfFloat": 0.009,
    }
    # DataFrames vides → parse_financial_df retourne None (géré proprement)
    m.balance_sheet = pd.DataFrame()
    m.income_stmt = pd.DataFrame()
    m.cashflow = pd.DataFrame()
    return m


# ── _refresh_momentum ─────────────────────────────────────────────────────────

class TestRefreshMomentum:

    def test_computes_all_three_metrics(self):
        from seeds.seed_live_prices import _refresh_momentum

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_price_history(250)

        with patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_ticker):
            result = _refresh_momentum("AAPL")

        assert "mm50" in result
        assert "mm200" in result
        assert "perf_1y" in result
        assert result["mm50"] is not None
        assert result["mm200"] is not None
        assert isinstance(result["perf_1y"], float)

    def test_empty_history_returns_empty_dict(self):
        from seeds.seed_live_prices import _refresh_momentum

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_ticker):
            result = _refresh_momentum("AAPL")

        assert result == {}

    def test_short_history_no_mm200(self):
        """60 clôtures : assez pour MM50, pas pour MM200."""
        from seeds.seed_live_prices import _refresh_momentum

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_price_history(60)

        with patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_ticker):
            result = _refresh_momentum("AAPL")

        assert result["mm50"] is not None
        assert result["mm200"] is None

    def test_perf_1y_reflects_price_growth(self):
        """Historique de 100 → 199 doit donner ~99 % de performance."""
        from seeds.seed_live_prices import _refresh_momentum

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = _make_price_history(250, start=100.0)

        with patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_ticker):
            result = _refresh_momentum("AAPL")

        # 250 valeurs : start=100, fin=100+249*0.5=224.5 → +124.5 %
        assert result["perf_1y"] == pytest.approx(124.5, abs=0.1)

    def test_yfinance_exception_returns_empty_dict(self):
        from seeds.seed_live_prices import _refresh_momentum

        mock_ticker = MagicMock()
        mock_ticker.history.side_effect = Exception("network timeout")

        with patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_ticker):
            result = _refresh_momentum("AAPL")

        assert result == {}


# ── _update_risk_market ───────────────────────────────────────────────────────

class TestUpdateRiskMarket:
    """Utilise une vraie session DB pour que flag_modified() fonctionne."""

    def test_creates_entries_on_empty_risk_market(self, db):
        from seeds.seed_live_prices import _update_risk_market

        company = Company(ticker="AAPL", name="Apple", risk_market=[])
        db.add(company)
        db.flush()

        _update_risk_market(company, {"mm50": 150.0, "mm200": 145.0, "perf_1y": 12.5})

        names = {m["name"] for m in company.risk_market}
        assert "MM50" in names
        assert "MM200" in names
        assert "Performance 1an" in names

    def test_updates_existing_entry_value(self, db):
        from seeds.seed_live_prices import _update_risk_market

        company = Company(
            ticker="AAPL", name="Apple",
            risk_market=[{"name": "MM50", "val": 100.0, "unit": "$"}],
        )
        db.add(company)
        db.flush()

        _update_risk_market(company, {"mm50": 155.0})

        entry = next(m for m in company.risk_market if m["name"] == "MM50")
        assert entry["val"] == 155.0

    def test_no_op_when_updates_empty(self, db):
        from seeds.seed_live_prices import _update_risk_market

        risk_original = [{"name": "MM50", "val": 100.0, "unit": "$"}]
        company = Company(ticker="AAPL", name="Apple", risk_market=risk_original)
        db.add(company)
        db.flush()

        _update_risk_market(company, {})

        assert len(company.risk_market) == 1
        assert company.risk_market[0]["val"] == 100.0

    def test_prix_actuel_entry_created(self, db):
        from seeds.seed_live_prices import _update_risk_market

        company = Company(ticker="AAPL", name="Apple", risk_market=[])
        db.add(company)
        db.flush()

        _update_risk_market(company, {"prix_actuel": 175.50})

        entry = next((m for m in company.risk_market if m["name"] == "Prix Actuel"), None)
        assert entry is not None
        assert entry["val"] == pytest.approx(175.50)

    def test_only_provided_keys_are_written(self, db):
        from seeds.seed_live_prices import _update_risk_market

        company = Company(ticker="AAPL", name="Apple", risk_market=[])
        db.add(company)
        db.flush()

        _update_risk_market(company, {"mm50": 150.0})  # pas mm200, pas perf_1y

        names = {m["name"] for m in company.risk_market}
        assert "MM50" in names
        assert "MM200" not in names
        assert "Performance 1an" not in names


# ── seed_fundamentals ─────────────────────────────────────────────────────────

class TestSeedFundamentals:
    """
    Patches appliqués dans chaque test :
      - TICKERS réduit à ["AAPL"] pour éviter 64 itérations
      - yf.Ticker remplacé par un mock → aucun appel réseau
      - SessionLocal remplacé par TestSessionLocal → SQLite in-memory
      - time.sleep → no-op pour accélérer les tests
    """

    def test_creates_company_in_db(self, session_factory):
        from seeds.seed_fundamentals import seed_fundamentals

        seed_session = session_factory()
        with (
            patch("seeds.seed_fundamentals.TICKERS", ["AAPL"]),
            patch("seeds.seed_fundamentals.yf.Ticker", return_value=_mock_yf_ticker()),
            patch("seeds.seed_fundamentals.time.sleep"),
            patch("seeds.seed_fundamentals.SessionLocal", return_value=seed_session),
        ):
            seed_fundamentals()

        verify = session_factory()
        company = verify.query(Company).filter_by(ticker="AAPL").first()
        assert company is not None
        assert company.name == "Apple Inc."
        assert company.sector == "Technology"
        assert company.asset_class == "stock"
        assert company.country == "United States"
        verify.close()

    def test_populates_all_metric_categories(self, session_factory):
        from seeds.seed_fundamentals import seed_fundamentals

        seed_session = session_factory()
        with (
            patch("seeds.seed_fundamentals.TICKERS", ["AAPL"]),
            patch("seeds.seed_fundamentals.yf.Ticker", return_value=_mock_yf_ticker()),
            patch("seeds.seed_fundamentals.time.sleep"),
            patch("seeds.seed_fundamentals.SessionLocal", return_value=seed_session),
        ):
            seed_fundamentals()

        verify = session_factory()
        c = verify.query(Company).filter_by(ticker="AAPL").first()
        assert c.market_analysis is not None
        assert any(m["name"] == "PER" for m in c.market_analysis)
        assert c.financial_health is not None
        assert any(m["name"] == "ROE" for m in c.financial_health)
        assert c.risk_market is not None
        assert c.advanced_valuation is not None
        verify.close()

    def test_updates_existing_company_without_duplicate(self, session_factory):
        from seeds.seed_fundamentals import seed_fundamentals

        # Pré-insérer AAPL avec un nom périmé
        setup = session_factory()
        setup.add(Company(ticker="AAPL", name="Old Apple Name"))
        setup.commit()
        setup.close()

        seed_session = session_factory()
        with (
            patch("seeds.seed_fundamentals.TICKERS", ["AAPL"]),
            patch("seeds.seed_fundamentals.yf.Ticker", return_value=_mock_yf_ticker()),
            patch("seeds.seed_fundamentals.time.sleep"),
            patch("seeds.seed_fundamentals.SessionLocal", return_value=seed_session),
        ):
            seed_fundamentals()

        verify = session_factory()
        assert verify.query(Company).filter_by(ticker="AAPL").count() == 1
        company = verify.query(Company).filter_by(ticker="AAPL").first()
        assert company.name == "Apple Inc."
        verify.close()

    def test_yfinance_exception_does_not_abort(self, session_factory):
        """Une erreur yfinance sur un ticker ne doit pas lever d'exception globale."""
        from seeds.seed_fundamentals import seed_fundamentals

        broken_ticker = MagicMock()
        broken_ticker.info = MagicMock(side_effect=Exception("network error"))

        seed_session = session_factory()
        with (
            patch("seeds.seed_fundamentals.TICKERS", ["AAPL"]),
            patch("seeds.seed_fundamentals.yf.Ticker", return_value=broken_ticker),
            patch("seeds.seed_fundamentals.time.sleep"),
            patch("seeds.seed_fundamentals.SessionLocal", return_value=seed_session),
        ):
            seed_fundamentals()  # ne doit pas lever d'exception

        verify = session_factory()
        assert verify.query(Company).count() == 0  # rien inséré après l'erreur
        verify.close()

    def test_asset_class_etf_override(self, session_factory):
        """CW8.PA doit être classé 'etf' même si yfinance renvoie EQUITY."""
        from seeds.seed_fundamentals import seed_fundamentals

        etf_info = {**_mock_yf_ticker().info, "quoteType": "EQUITY", "shortName": "Amundi MSCI World"}
        mock_etf = MagicMock()
        mock_etf.info = etf_info
        mock_etf.balance_sheet = pd.DataFrame()
        mock_etf.income_stmt = pd.DataFrame()
        mock_etf.cashflow = pd.DataFrame()

        seed_session = session_factory()
        with (
            patch("seeds.seed_fundamentals.TICKERS", ["CW8.PA"]),
            patch("seeds.seed_fundamentals.yf.Ticker", return_value=mock_etf),
            patch("seeds.seed_fundamentals.time.sleep"),
            patch("seeds.seed_fundamentals.SessionLocal", return_value=seed_session),
        ):
            seed_fundamentals()

        verify = session_factory()
        company = verify.query(Company).filter_by(ticker="CW8.PA").first()
        assert company.asset_class == "etf"
        verify.close()


# ── seed_live_prices (intégration) ────────────────────────────────────────────

class TestSeedLivePrices:

    def _fmp_response(self, price=180.0, change=1.5):
        """Mock d'une réponse FMP réussie."""
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = [{"price": price, "changePercentage": change}]
        return r

    def test_updates_live_price_and_change(self, session_factory):
        from seeds.seed_live_prices import seed_live_prices

        setup = session_factory()
        setup.add(Company(ticker="AAPL", name="Apple", sector="Technology"))
        setup.commit()
        setup.close()

        mock_yf = MagicMock()
        mock_yf.history.return_value = _make_price_history(250)

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = self._fmp_response(180.0, 1.5)

        with (
            patch("seeds.seed_live_prices.SessionLocal", session_factory),
            patch("seeds.seed_live_prices.check_and_increment", return_value=("ok", 1)),
            patch("seeds.seed_live_prices.get_count", return_value=2),
            patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_yf),
            patch("seeds.seed_live_prices.httpx.Client", return_value=mock_http),
            patch("seeds.seed_live_prices.time.sleep"),
        ):
            seed_live_prices(["AAPL"])

        verify = session_factory()
        company = verify.query(Company).filter_by(ticker="AAPL").first()
        assert company.live_price == pytest.approx(180.0)
        assert company.live_change_pct == pytest.approx(1.5)
        assert company.live_price_at is not None
        verify.close()

    def test_circuit_breaker_skips_fmp_call(self, session_factory):
        """Quand check_and_increment retourne 'blocked', aucune donnée FMP ne doit être écrite."""
        from seeds.seed_live_prices import seed_live_prices

        setup = session_factory()
        setup.add(Company(ticker="AAPL", name="Apple", sector="Technology"))
        setup.commit()
        setup.close()

        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)

        with (
            patch("seeds.seed_live_prices.SessionLocal", session_factory),
            patch("seeds.seed_live_prices.check_and_increment", return_value=("blocked", 245)),
            patch("seeds.seed_live_prices.get_count", return_value=245),
            patch("seeds.seed_live_prices.yf.Ticker", return_value=MagicMock()),
            patch("seeds.seed_live_prices.httpx.Client", return_value=mock_http),
            patch("seeds.seed_live_prices.time.sleep"),
        ):
            seed_live_prices(["AAPL"])

        verify = session_factory()
        company = verify.query(Company).filter_by(ticker="AAPL").first()
        assert company.live_price is None  # pas mis à jour car circuit ouvert
        verify.close()

    def test_ticker_absent_from_db_is_skipped_gracefully(self, session_factory):
        """Un ticker FMP non présent en DB ne doit pas lever d'exception."""
        from seeds.seed_live_prices import seed_live_prices

        mock_yf = MagicMock()
        mock_yf.history.return_value = _make_price_history(250)
        mock_http = MagicMock()
        mock_http.__enter__ = MagicMock(return_value=mock_http)
        mock_http.__exit__ = MagicMock(return_value=False)
        mock_http.get.return_value = self._fmp_response()

        with (
            patch("seeds.seed_live_prices.SessionLocal", session_factory),
            patch("seeds.seed_live_prices.check_and_increment", return_value=("ok", 1)),
            patch("seeds.seed_live_prices.get_count", return_value=1),
            patch("seeds.seed_live_prices.yf.Ticker", return_value=mock_yf),
            patch("seeds.seed_live_prices.httpx.Client", return_value=mock_http),
            patch("seeds.seed_live_prices.time.sleep"),
        ):
            seed_live_prices(["TICKER_ABSENT"])  # ne doit pas lever d'exception
