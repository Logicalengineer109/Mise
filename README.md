# Mise

*Mise en place* — everything prepped and in its place. A small ETL pipeline that fetches
live business data from the Yelp Fusion API and loads it into Postgres, with a local web
UI for running searches and browsing what landed in the table.

## Overview

Two ways to run the same pipeline:

- **CLI** — `./run.sh --term food --location Montreal --price 4`
- **Web UI** — `./run_web.sh`, then open http://127.0.0.1:5055

Both paths share the same code: `BusinessSearch` parses the API response, `queries.py`
holds the DDL and the upsert, and `DatabaseDriver` talks to Postgres.

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
createdb mise
```

Then copy `config.cfg.example` to `config.cfg` and fill it in:

```
[KEYS]
CLIENT_KEY=
API_KEY=<YOUR 128-CHARACTER YELP FUSION API KEY>

[DATABASE]
host=localhost
database=mise
username=<USER NAME>
password=<PASSWORD>
port=5432
```

A Yelp Fusion key is required for live data — get one at
https://www.yelp.com/developers (Create App). Yelp rejects anything that is not a
128-character key with a `400 VALIDATION_ERROR`. Without a key the web UI still runs in
**sample data** mode, which feeds an offline payload through the real parse-and-load path.

## Files

```
driver.py          - CLI entry point: argument parsing and program flow
auth.py            - reads config.cfg, builds the Authorization header
request.py         - HTTP request handling, reports API error details
businesssearch.py  - parses the business search response into table rows
queries.py         - schema/table DDL and the upsert statement
databasedriver.py  - Postgres connection and query execution
run.sh             - runs the CLI pipeline with the project virtualenv
run_web.sh         - starts the web UI on port 5055

webapp/
  app.py                   - Flask app wrapping the pipeline
  templates/index.html     - control panel
  static/style.css         - styles
  static/app.js            - row filter, column sort, Leaflet map
  sample_businesses.json   - offline payload for sample mode
```

## Web UI

- Search by term, location and price tier, against the live API or sample data
- Header pills show whether Postgres is reachable and whether a valid API key is present
- Stat tiles: business count, average rating, total reviews, distinct categories
- Map of geocoded businesses (Leaflet), with rating/reviews/price popups
- Sortable, filterable table of `yelp.business`, plus a clear-table action
- `GET /api/businesses` returns the loaded rows as JSON

## Schema

Loaded into schema `yelp`, table `business`, keyed on `business_id` with
`ON CONFLICT DO UPDATE`, so re-running a search refreshes rows instead of duplicating them.

## Credits

The core ETL pipeline (`driver.py`, `businesssearch.py`, `databasedriver.py`, `queries.py`,
`auth.py`, `request.py`) is derived from
[san089/Udacity-Data-Engineering-Projects](https://github.com/san089/Udacity-Data-Engineering-Projects),
Copyright (c) 2020 Sanchit Kumar, MIT licensed — see `LICENSE`.

Added in this repository: the Mise web UI (`webapp/`), sample-data mode, defensive parsing of
optional Yelp fields, API error reporting, and the run scripts.
