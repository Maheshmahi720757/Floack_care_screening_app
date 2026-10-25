# FlockCare — Flock Screening Dashboard

A small Streamlit app for storing bird screening records and reviewing flock observations.

## Features
- Add records: bird ID, flock ID, screening date, symptoms, result, optional notes
- Persistent local SQLite database
- Dashboard metrics: total records, unique birds, flocks, flagged records
- Charts for flagged observations over time and screening-result counts
- Filterable screening history and CSV export
- Optional deletion of an individual record

## Run it
Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app creates `flock_screenings.db` in the same folder. Keep that file to retain records and back it up regularly.

## Note
This is a local prototype. To make it accessible to multiple users online, configure a hosted database and persistent deployment storage. A flagged screening is not a diagnosis.
