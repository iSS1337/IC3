# IC3 - SensorTwin S1: motor turbofan (C-MAPSS), durata de viata ramasa (RUL)

Proiect la Inteligenta Computationala III (SIVA, anul II): un mini digital twin construit strat cu strat (observatii, reprezentare, invatare, predictie, interpretare, decizie), cu un articol si un mockup la final.

**Autor:** Ciobanu Marius-Sebastian

## Intrebarea de cercetare
Cat de devreme poate un planificator de mentenanta sa programeze oprirea unui motor turbofan, cu risc controlat de defect neanuntat, pornind doar de la datele senzorilor?

**Client si decizie:** planificatorul de mentenanta al unei flote - alege cand si pentru ce motor programeaza oprirea la hangar. **Tinta:** RUL (Remaining Useful Life) cu incertitudine.

## Date
NASA C-MAPSS (FD001-FD004), date simulate. Descarcare si licenta: `data/README.md` (datele nu se urca in git).

## Stare pe checkpoint-uri
| CP | Strat | Livrabil | Stare |
|---|---|---|---|
| CP0 | Concept | `checkpoints/CP0_CIOBANU-Marius-Sebastian.pdf` | predat |
| CP1 | Observatii | `checkpoints/CP1_CIOBANU-Marius-Sebastian.pdf`, `docs/data_card.md`, `docs/sota_table.csv`, `src/ingest.py` | predat |

Etichete git: `CP0`, `CP1` marcheaza starea exacta la fiecare checkpoint.

## Continut
- `docs/data_card.md` - data card FD001-FD004 (compozitie, constatari din date, discrepanta FD004, reguli anti-leakage, limitari).
- `docs/sota_table.csv` - tabel SOA: 10 lucrari pe C-MAPSS (+2 de rezerva), cu sub-seturi, metoda, protocol, rezultate si incertitudine.
- `src/ingest.py` - ingestie, RUL, normalizare per regim (potrivita doar pe train), split pe motoare, ferestre, verificari de integritate.
- `src/leakage_demo.py` - demonstratie de leakage (rezultat in `docs/leakage_demo.json`).

## Reproducere
```
pip install -r requirements.txt
# descarca datele in data/raw/ (vezi data/README.md)
python src/ingest.py --data data/raw
python src/leakage_demo.py --data data/raw
```
