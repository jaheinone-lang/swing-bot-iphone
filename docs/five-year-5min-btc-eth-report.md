# BTC + ETH: viiden vuoden päivätreidaussimulaatio

**Tarkistettu:** 23.10.2026. **Aikaväli:** 23.10.2021 klo 00.00 UTC – 23.10.2026 klo 00.00 UTC (loppu pois lukien). Tutkimusversio, ei todellisia toimeksiantoja.

**Varmennettu GitHub Actions -ajo:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39902956449 . Mukana ladattava `btc-eth-five-year-5m-results`-JSON-raportti.

## Markkinadata ja luotettavuus

- Lähde: **Bitvavon julkiset BTC-EUR/ETH-EUR-kaupankäynnit**, aidot 5 minuutin OHLCV-kynttilät. Ei USD-muunnoksia, ei vaihdettuja pörssejä, ei tuntikynttilöiksi yhdistelyä. Maksimi **1 440 kynttilää/pyyntö**, yhteensä **732** rajatusti tahdistettua julkista pyyntöä.
- Odotettavissa 525 888 kynttilää per markkina. **BTC havaittu 523 661**, puuttuvia 2 227 (99,577 %). **ETH havaittu 521 788**, puuttuvia 4 100 (99,220 %).
- **Yhteiset aikaleimat 520 943**. Vain vähintään 180 kynttilän katkeamattomat jaksot sallitaan tutkimuksessa; **505 799 kelpuutettua kynttilää** / **691 erillistä yhtenäistä jaksoa**. Näiden ulkopuolisista jaksoista ei väitetä kauppatuloksia.
- Historiakatkon lopussa avoin positio oletetaan myydyksi viimeisellä havaintohinnalla ja kuluilla. Uudessa segmentissä indikaattorit vaativat 160 kynttilän lämmittelyn. Datakatkot ja uudelleenkäynnistykset voivat vääristää tulosta; tämä EI ole aukoton 5 vuoden replay.
- Suomi `Europe/Helsinki`, kesä- ja talviaika; enintään 1 osto kumpaakaan instrumenttia yhteensä per suomalainen kalenteripäivä.
- Sijoitus **yhdeltä yhteiseltä 5 000 €:n alkutililtä**, riskipohjainen position koko, alussa enintään noin 0,25 % nimellistä stop-riskiä/kauppa ja 20 % koko tilin positioraja, ei velkavipua.
- Osto vain edellisen valmiin 5 min kynttilän nousevasta signaalista **seuraavan 5 min kynttilän avauksessa**. Koko position +1,00 % ennakoitujen osto- ja myyntikulujen jälkeiseen nettotavoitteeseen saavuttaminen -> 100 % myynti oletettuun tavoitehintaan. Muuten stop-loss tai Suomen ajan klo 21.55 sulku; stop ennen tavoitetta, jos saman kynttilän epäselvä kosketus.
- Oletuskulut kummallakin puolella 0,25 % kaupankäyntipalkkio ja 0,15 % liukuma. Stressimallissa kummallakin puolella **0,50 % + 0,30 %**. Henkilökohtainen pääomatuloverotus ei sisälly.

## Viiden vuoden tulos yhteisestä 5 000 €:n tilistä

| Ostomalli | Ostot | Täydet +1 % nettovoittomyynnit | Stopit | Klo 21.55 sulut | Loppusaldo € | PnL € | Tuotto % | Loppu 2× kulut € | PnL 2× kulut € |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Vahvistettu nousu klo 09–20 | 278 | 69 | 118 | 89 | 3 743,50 | −1 256,50 | −25,13 % | 3 405,07 | −1 594,93 |
| Vahvistettu nousu klo 09–14 | 105 | 33 | 56 | 14 | 4 477,04 | −522,96 | −10,46 % | 4 322,36 | −677,64 |
| **Tiukka nousu klo 09–14** | **50** | **17** | **27** | **5** | **4 749,60** | **−250,40** | **−5,01 %** | **4 652,59** | **−347,41** |

Eri mallien tuloksissa on lisäksi datakatkoksiin liittyviä pakkosulkuja.

## Parhaiten (eli vähiten tappiollinen) tiukan aamumallin vuosittainen tulos

| Vuosi | Ostot | Täydet 1 %:n TP:t | Vuoden simuloitu euromääräinen tulos |
|---|---:|---:|---:|
| 2021 (23.10.–31.12.) | 4 | 1 | −31,98 € |
| 2022 | 4 | 1 | −31,77 € |
| 2023 | 1 | 0 | −12,34 € |
| 2024 | 19 | 4 | −111,87 € |
| 2025 | 13 | 4 | −86,58 € |
| 2026 (1.1.–22.10.) | 9 | 7 | +24,13 € |
| **Yhteensä** | **50** | **17** | **noin −250,40 €** |

Vuosien euromäärät ovat toteutuneiksi oletettujen myyntien kirjauksia, kunkin segmentin senttipyöristys vaikuttaa summan loppusentteihin. Vuosi 2026 oli tiukassa mallissa hieman plussalla peruskuluilla, mutta **−15,73 €** 2× kuluilla. Aikaisempina vuosina vastaava malli oli tappiollinen.

## Mitä tämä todistaa / ei todista

- **Ei positiivista koko viiden vuoden historiallista tuotto-odotusta** millään kolmesta testatusta säännöstä. Siksi ei automaattista hyväksyntää oikealle rahalle.
- Tiukempi aamumalli vähensi historiallisen tappion −1 256,50 € → −250,40 €, koska se vähensi ostot 278:sta 50:een; se ei tehnyt 1 % voittoa joka päivä, eikä kaupankäynnistä joka päivä.
- Tiukan mallin 17 toteutuneeksi oletettua TP-myyntiä / 50 ostoa tarkoittaa 34 % koko position nettotavoitteen osumatodennäköisyyttä tutkimuksen markkinadatalla (ei tulevaa ennustetta).
- Voitollisen kaupan keskimääräinen saldoon kirjautuva voitto oli **+5,24 €**, ei +50 €. Nettotavoite koskee riskiperusteisesti rajattua ostettua positiota, ei koko alkuperäistä 5 000 €:n pääomaa.
- Suurimmat epävarmuudet: order book / toteutuuko target-täyttö, kynttilöiden 5 min sisäinen tapahtumajärjestys, toteutuvat slippaget ja spread, datakatkojen pakkolikvidointi, strategiasääntöjen jälkikäteinen valinta 2026 havaintojen perusteella sekä Suomen verotus.
- Raportoitava seuraava kehitys on **lukittu tulevaisuuden paperikaupankäynti ja uudet, ennestään tarkastelemattomat ostot**. Menneisyyden optimointi voi antaa harhaanjohtavan hyvän tuloksen, eikä mikään hyväksyntäraja nyt täyttynyt.

**Ei live-kauppoja eikä muutoksia vanhaan Momentum E -forward paperisalkkuun.** Kaikki tutkimushaaran draft-PR:ssä.
