# AI Job Hunter (Deutschland)

Lokales, KI-gestütztes System zur automatisierten Jobsuche: Scraping von Jobbörsen und verstecktem Arbeitsmarkt, Filter nach Ort (25 km um Elsdorf, Kerpen, Sindorf), Gehalt (min. 37.000 € brutto/Jahr) und Relevanz, Erstellung wahrheitsgemäßer Anschreiben sowie einseitiger Interview-Briefs. Alle Bewerbungen werden in einer SQLite-Datenbank geführt.

## Voraussetzungen

- Python 3.10+
- OpenAI API-Key (für Anschreiben, Interview-Briefs, Relevanz- und Gehaltsschätzung)

## Installation

```bash
cd ai-job-hunter
pip install -r requirements.txt
```

## Konfiguration

1. **API-Key:** In `config/` eine Datei `.env` anlegen (siehe `config/.env.example`):
   ```
   OPENAI_API_KEY=dein-openai-api-key
   ```

2. **Job-Einstellungen:** `config/job_preferences.json` anpassen:
   - `locations`: Elsdorf, Kerpen, Sindorf (und ggf. weitere)
   - `radius_km`: 25
   - `min_salary_gross_year`: 37000
   - `search_keywords`: Suchbegriffe für die Scraper
   - `job_boards`: "indeed", "stepstone", "linkedin"
   - `hidden_job_queries`: Google-Dork-artige Suchanfragen (für Hidden-Job-Scraper, siehe unten)

3. **Profil:** Optional `config/user_profile.json` anpassen.

4. **Lebenslauf und Arbeitszeugnisse:** PDF-Dateien ablegen:
   - `config/lebenslauf.pdf`
   - `config/arbeitszeugnisse.pdf`  
   Ohne diese Dateien funktioniert der Relevanzfilter mit leerem Profil (alle Jobs werden als „zur Prüfung“ markiert).

5. **Unternehmens-Karriereseiten:** Optional `data/companies/companies.csv` anlegen (Format siehe `data/companies/companies.csv.example`):
   - Spalten: `company_name`, `career_page_url`, optional `location`

6. **Hidden Job Market (Google):** Optional für den Hidden-Job-Scraper in `config/.env`:
   - `GOOGLE_API_KEY` und `GOOGLE_CSE_ID` (Google Custom Search Engine) eintragen.

## Ausführung

- **Voller Tageslauf (empfohlen):**
  ```bash
  python main.py --daily
  ```
  Führt aus: Scraping aller Quellen → Parsing → Ort-Filter (25 km) → Gehaltsfilter (≥ 37k) → Relevanzfilter (Lebenslauf/Arbeitszeugnisse) → für jeden verbleibenden Job: Anschreiben + Interview-Brief erzeugen und in der DB als „saved“ speichern.

- **Nur Scraping:**
  ```bash
  python main.py --scrape-only
  ```
  Schreibt die geparsten Jobs nach `data/jobs/latest.json`.

- **Nur Filter (auf bestehender `data/jobs/latest.json`):**
  ```bash
  python main.py --filter-only
  ```

**Wichtig:** Das System **sendet keine Bewerbungen automatisch**. Es bereitet nur vor. Den Status „applied“ setzt der Nutzer manuell (z. B. über eine spätere Erweiterung oder direkt in der DB), nachdem er die Bewerbung abgeschickt hat.

## Ausgaben

- **Anschreiben:** `outputs/anschreiben/<Firma>_<Rolle>.txt`
- **Interview-Briefs:** `outputs/interview_briefs/<Firma>_<Rolle>.txt`
- **Datenbank:** `data/applications.db` (SQLite, Tabelle `applications` mit Status: saved, applied, interview, rejected, offer)
- **Logs:** `logs/scraper.log`, `logs/filter.log`, `logs/applications.log`, `logs/errors.log`

## Projektstruktur

- `config/` – Konfiguration, Lebenslauf/Arbeitszeugnisse (PDF)
- `scrapers/` – Indeed, StepStone, LinkedIn, Hidden Job (Google CSE), Unternehmens-Karriereseiten
- `processing/` – PDF-Extraktion, job_parser, location_filter, salary_filter, job_relevance_filter
- `ai_modules/` – OpenAI-Client, Anschreiben-Generator, Interview-Brief-Generator
- `automation/` – application_assistant (Tagesworkflow)
- `database/` – database_manager (SQLite)
- `data/jobs/`, `data/companies/` – Rohdaten
- `outputs/anschreiben/`, `outputs/interview_briefs/`
- `logs/`

## Skalierung / Erweiterungen

- Weitere Jobbörsen oder ATS (z. B. Workable, SmartRecruiters) als neue Scraper in `scrapers/` ergänzen.
- Radius und Orte in `config/job_preferences.json` anpassen; `config/locations_geo.json` bei neuen Orten erweitern.
- Weitere Firmen in `data/companies/companies.csv` eintragen.
- Täglichen Lauf per Scheduler (Cron, Windows Task Scheduler) mit `python main.py --daily` ausführen.
- Optional: Kleine CLI- oder Web-UI zum Setzen des Status „saved“ → „applied“ und zum Anzeigen von Anschreiben/Briefs.

## Hinweise

- Scraping von Indeed, StepStone und LinkedIn kann gegen Nutzungsbedingungen verstoßen oder zu Blockaden führen; defensiv nutzen (Rate-Limits, Backoff). LinkedIn rendert viele Inhalte per JavaScript – der LinkedIn-Scraper liefert nur begrenzt Ergebnisse.
- Der Hidden-Job-Scraper nutzt die Google Custom Search API (mit API-Key und CSE-ID); ohne Eintrag in `.env` wird er übersprungen.
