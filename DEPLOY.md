# Deploying the app

**Live at <https://trader-sentiment-demo.streamlit.app/>.**

> **The app must be set to public.** In Streamlit Community Cloud open the app →
> **Settings → Sharing** → set viewer access to *"Anyone with the link"* (public).
> While it is private the URL answers `303` and redirects visitors to a login page,
> which for a portfolio link is worse than having no link at all.

The app is a single Streamlit page (`app.py`) showing the contrarian edge per
sentiment band, the live Fear & Greed index, and the caveats that matter.

## Streamlit Community Cloud (free)

1. Sign in at <https://share.streamlit.io> with this GitHub account.
2. **New app** → repository `VishnujanNarayanan/Trader_sentiment_analysis`,
   branch `main`, main file path `app.py`.
3. Under **Advanced settings**, set the requirements file to
   `requirements-app.txt` (narrower than the dev requirements — the deployed app
   needs neither the notebook stack nor the test tooling).
4. Deploy. The first build takes a couple of minutes.

The 47MB trade export is not in the repository, so the deployed app runs against
a precomputed summary of the full 167,331-trade result and says so in a banner.
That is deliberate: a link that greets a visitor with a stack trace is worse than
no link. The live Fear & Greed chart still fetches from the public API, so the
page is not static.

To serve the app against the real export, mount it and set `TS_TRADES_CSV`:

```bash
TS_TRADES_CSV=/path/to/historical_data.csv streamlit run app.py
```

## Locally

```bash
pip install -r requirements-app.txt
streamlit run app.py          # http://localhost:8501
```

## In Docker

```bash
docker build -t trader-sentiment .
docker run --rm -p 8501:8501 -v "$PWD/data:/data" \
  trader-sentiment streamlit run app.py --server.address 0.0.0.0
```
