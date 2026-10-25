# Data card - NASA C-MAPSS (FD001-FD004)

Format: Datasheets for Datasets (Gebru et al.), condensat. Toate cifrele de mai jos sunt calculate din fisierele locale cu `src/ingest.py` (verificari rulate pe 25.10.2026).

## 1. Identitate

| | |
|---|---|
| Nume | C-MAPSS - Commercial Modular Aero-Propulsion System Simulation, "CMAPSS Jet Engine Simulated Data" |
| Sursa | NASA Prognostics Center of Excellence (PCoE), data.nasa.gov, resursa `CMAPSSData.zip` |
| Origine stiintifica | A. Saxena, K. Goebel, D. Simon, N. Eklund, *Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation*, PHM08, Denver, 2008 |
| Licenta | Nespecificata pe pagina resursei ("License not specified"). Datele nu sunt prezentate ca domeniu public. |
| Natura datelor | **Simulate** (model termodinamic de turbofan din clasa de 90 000 lb tractiune, mediu MATLAB/Simulink), nu masuratori de pe motoare reale |
| Format | Text ASCII, separat prin spatii, **26 de coloane**, fara antet, spatiu la final de rand |

## 2. Scop si client

Date create pentru PHM08 Data Challenge: estimarea duratei de viata ramase (RUL) dintr-o flota de motoare, doar din date istorice. In acest proiect: RUL cu incertitudine, pentru decizia planificatorului de mentenanta (cand opreste un motor la hangar).

## 3. Compozitie

Fiecare sub-set are un fisier `train` (traiectorii complete, pana la defect), unul `test` (traiectorii **oprite inainte de defect**) si un fisier `RUL` (RUL real la ultimul ciclu observat al fiecarui motor de test). Fiecare motor este o serie temporala separata; fiecare sub-set este o flota distincta.

| Sub-set | Motoare train / test | Randuri train / test | Conditii de operare | Moduri de defect |
|---|---|---|---|---|
| FD001 | 100 / 100 | 20 631 / 13 096 | 1 | 1 (HPC) |
| FD002 | 260 / 259 | 53 759 / 33 991 | 6 | 1 (HPC) |
| FD003 | 100 / 100 | 24 720 / 16 596 | 1 | 2 (HPC + Fan) |
| FD004 | **249 / 248** | 61 249 / 41 214 | 6 | 2 (HPC + Fan) |

**Lungimea traiectoriilor (cicluri)**

| Sub-set | Train min / medie / mediana / max | Test min / medie / max | RUL test min / medie / max | Motoare test cu RUL > 125 |
|---|---|---|---|---|
| FD001 | 128 / 206,3 / 199 / 362 | 31 / 131,0 / 303 | 7 / 75,5 / 145 | 11 din 100 |
| FD002 | 128 / 206,8 / 199 / 378 | 21 / 131,2 / 367 | 6 / 81,2 / 194 | 57 din 259 |
| FD003 | 145 / 247,2 / 220,5 / 525 | 38 / 166,0 / 475 | 6 / 75,3 / 145 | 15 din 100 |
| FD004 | 128 / 246,0 / 234 / 543 | 19 / 166,2 / 486 | 6 / 86,6 / 195 | 67 din 248 |

In test se observa in medie 61-66% din viata totala a motorului (ciclurile observate / (observate + RUL real)).

**Coloanele (in ordinea din fisier)**

1. `unit` - id motor (1...N; numerotarea se repeta in train si test: id-ul **nu** leaga un motor de train de unul de test)
2. `cycle` - ciclu (zbor), contiguu de la 1
3-5. `os1, os2, os3` - setari operationale (in literatura: altitudine, numar Mach, unghiul manetei; readme-ul NASA nu le numeste)
6-26. `s1...s21` - senzori. Descriere dupa Tabelul 2 din Saxena et al. 2008, in ordinea tabelului: T2, T24, T30, T50 (grade Rankine); P2, P15, P30 (psia); Nf, Nc (rpm); epr (fara unitate); Ps30 (psia); phi (pps/psi); NRf, NRc (rpm); BPR, farB, htBleed (fara unitate); Nf_dmd, PCNfR_dmd (rpm); W31, W32 (lbm/s). Corespondenta `sK` - randul K din tabel este conventia folosita in literatura; readme-ul NASA nu o enunta explicit.

**Integritate**: 0 valori lipsa, 0 randuri duplicate, cicluri contigue la toate motoarele (train si test), numarul de randuri din `RUL_FDxxx` este egal cu numarul de motoare de test, id-urile coincid.

## 4. Proces de generare

- Fiecare motor porneste cu **uzura initiala si variatii de fabricatie necunoscute**, considerate normale (nu defect). Defectul apare la un moment al seriei si creste pana la defect (in train) - conform readme-ului si lucrarii Saxena et al.
- Degradarea: pierdere exponentiala de debit si eficienta pe modulul vizat; indicele de sanatate este minimul mai multor marje operationale, iar defectul este atins cand acesta ajunge la zero (Saxena et al.). Marjele **nu** sunt disponibile participantilor.
- Datele contin **zgomot de senzor** (mixtura de zgomote), conform readme-ului si lucrarii.
- Conditii multiple (FD002, FD004): regimul de operare se schimba de la un ciclu la altul, deci valorile senzorilor sunt dominate de regim, nu de degradare, pana la normalizarea per regim.

## 5. Constatari din date (relevante pentru pipeline)

**5.1 Senzori fara variatie** (abatere standard < 1e-6, in interiorul fiecarui regim):

| Sub-set | Senzori inerti |
|---|---|
| FD001 | s1, s5, s10, s16, s18, s19 |
| FD002 | s1, s5, s18, s19 |
| FD003 | s1, s5, s16, s18, s19 |
| FD004 | s1, s5, s18, s19 |

In plus, `s6` (FD001) si `s10` (FD003) au foarte putine valori distincte. `s6` nu este strict constant in FD001; eliminarea lui ar fi o decizie de modelare, nu o proprietate a datelor.

**5.2 Cuantizare in regimuri.** In FD002, `s10` are 1-2 valori distincte in fiecare regim (de exemplu 1,07 si 1,08), iar in FD004 `s16` are 1-2 valori distincte in fiecare regim. Un z-score per regim transforma un singur salt de cuantizare in |z| ~ 50 (FD002 `s10`: 51,9; FD004 `s16`: 48,0). `ingest.py` pune acesti senzori pe 0 in regimurile unde au cel mult 2 valori; dupa aceasta protectie |z| maxim este 8,9 pe toate sub-seturile.

**5.3 Regimuri.** FD002 si FD004 au 6 regimuri (combinatii `os1/os2/os3`). Frecventele nu sunt egale: cinci regimuri au ~8 000 de randuri (FD002) / ~9 200 (FD004), iar al saselea (`os1 ~ 42, os2 ~ 0,84, os3 = 100`) are 13 458 / 15 395 (~25%).

**5.4 Motoare scurte in test.** Cu fereastra de 30 de cicluri, motoarele de test cu mai putin de 30 de cicluri necesita umplere (padding): FD002 6 motoare, FD004 11, FD001 si FD003 niciunul. Cu mai putin de 50 de cicluri: 7 / 24 / 3 / 20 (FD001 / FD002 / FD003 / FD004).

**5.5 Plafonul de RUL.** RUL real din test depaseste 125 la 11% (FD001), 22% (FD002), 15% (FD003) si 27% (FD004) din motoare. Evaluarea cu RUL plafonat la 125 nu este echivalenta cu evaluarea pe RUL real; trebuie raportat explicit ce se foloseste (vezi `docs/sota_table.csv`: lucrarile nu raporteaza uniform).

## 6. Discrepanta documentata: FD004 = 249 train / 248 test

- `readme.txt` din arhiva indica 248 train / 249 test.
- **Fisierele indica 249 train / 248 test** (id-uri unice numarate in `train_FD004.txt` si `test_FD004.txt`; `RUL_FD004.txt` are 248 de randuri).
- Literatura foloseste ambele variante: Javanmardi & Hullermeier (2022) dau 249/248, Thil et al. (2025) dau 248/249.
- Se folosesc cifrele din fisiere. Verificarea este automata in `ingest.py`.

## 7. Utilizare recomandata si prevenirea scurgerilor de informatie (leakage)

1. **Split pe motoare**, niciodata pe randuri sau pe ferestre. Ferestrele glisante de 30 de cicluri ale aceluiasi motor se suprapun 29/30; un split aleator le pune pe ambele parti. (`ingest.group_split`.)
2. **Normalizarea se potriveste doar pe train** (per regim in FD002/FD004) si se aplica apoi pe validare/test. (`ingest.regime_normalizer`.)
3. **Testul oficial = ultimul ciclu al fiecarui motor**, cu RUL din `RUL_FDxxx.txt`. Un motor de test nu are RUL cunoscut pe celelalte cicluri; nu se construiesc etichete pe ele.
4. **Nu se selecteaza hiperparametri sau senzori pe testul oficial.**
5. Id-urile `unit` din train si test sunt independente: nu se face join pe ele.
6. Se raporteaza: plafonul RUL, lungimea ferestrei, numarul de seed-uri, metrica pe ultimul ciclu (RMSE si scorul NASA).

**Demonstratie de leakage (FD001, k-NN cu k=5, 5 seed-uri)** - `src/leakage_demo.py`, rezultat in `docs/leakage_demo.json`: split aleator pe randuri 19,72 +/- 0,28 RMSE vs. pe motoare 19,51 +/- 0,92; ferestre de 30 de cicluri, split aleator 18,26 +/- 0,37 vs. pe motoare 19,37 +/- 1,73. Diferenta este mica si in limita zgomotului pentru acest model simplu. Regula (split pe motoare) ramane obligatorie pentru modele cu capacitate de memorare.

## 8. Limitari

- **Date simulate**: fara deriva, defecte si intretinere reale; rezultatele nu se transfera automat pe flote reale (limitare asumata in articol).
- Un singur set de moduri de defect (HPC, Fan); alte componente nu sunt modelate.
- Conditiile de zbor sunt anonimizate; impreuna cu senzorii nu constituie a doua sursa de date heterogena in sens strict.
- Marimea (100-260 de motoare per flota) face ca evaluarea oficiala pe ultimul ciclu sa aiba varianta mare; de aici nevoia de seed-uri si intervale.
- Comparabilitatea cu literatura este limitata: plafonul RUL, fereastra, selectia pe test si raportarea "celui mai bun run" difera intre lucrari.

## 9. Distributie si intretinere

Datele nu se urca in git (`data/raw/` in `.gitignore`); `data/README.md` descrie descarcarea din `https://data.nasa.gov/docs/legacy/CMAPSSData.zip`. Fisiere locale folosite: `data/raw/{train,test,RUL}_FD00{1-4}.txt`. Autor: Ciobanu Marius-Sebastian.

## 10. Reproducere

```
python src/ingest.py --data data/raw      # integritate + verificari anti-leakage, tipareste sumarul
python src/leakage_demo.py --data data/raw # demonstratia de leakage (~6 s)
```
Cerinte: Python >= 3.9, numpy, pandas (versiuni fixate in `requirements.txt`).
