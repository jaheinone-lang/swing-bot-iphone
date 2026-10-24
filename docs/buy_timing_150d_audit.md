# BTC + ETH — 150 päivän ostotapahtumien auditointi

Päivämäärä 23.10.2026. [Onnistunut GitHub Actions -testi](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39901005835).

Tutkimuskoodi: `swingbot/entry_timing_150d_audit.py`. Tests: `tests/test_entry_timing_150d_audit.py`.

**TARKOITUS:** Etsiä jo tapahtuneista kryptokaupoista onnistuneisiin päivänsisäisiin nousuihin liittyvät *ostohetkeä ennen tunnetut* signaalipiirteet. Vain BTC-EUR ja ETH-EUR, yksi yhteinen 5 000 € salkku, enintään yksi osto Suomen kalenteripäivässä yhteensä, 100 %:n myynti +1 %:n laskennallisella nettovoitolla, stop-loss tai klo 21.55 pakkosulku. Osto seuraavan viiden minuutin kynttilän avauksessa. Ei pörssitoimeksiantoja.

150 päivän aineistossa BTC/ETH-kohdistettuja todellisia viiden minuutin kynttilöitä 43 141; historiassa aukkoja, joita ei täytetä. Ensimmäiset 90 päivää erillisiin tutkimusjaksoihin ja myöhemmät 60 päivää kronologiseen vertailuun, joka ei ole täydellisen riippumaton myöhemmän mallikehityksen ulkopuolella, koska näitä hintoja on analysoitu jo aiemmin.

## Myöhempien 60 päivän vertailu — kukin oma yhteinen BTC/ETH 5 000 € testisalkku

| Ostosääntö | 90 pv vanhemman jakson tulos | 90 pv 2× kulut | 60 pv myöhempi tulos | 60 pv 2× kulut | Myöhemmät ostot | Myöhemmät +1 % TP |
|---|---:|---:|---:|---:|---:|---:|
| Vahvistettu nousu, 09–20 | −36,91 € | −66,57 € | −25,65 € | −40,68 € | 8 | 2 |
| Vahvistettu nousu, **09–14** | −8,62 € | −23,20 € | **+6,37 €** | −0,85 € | 3 | 2 |
| Vahvistettu nousu, **14–20** | −28,34 € | −43,58 € | −38,67 € | −51,24 € | 7 | 0 |
| Vahvistettu nousu, volyymi ≥1,6× | −20,78 € | −45,06 € | −8,34 € | −21,45 € | 6 | 2 |
| Vahvistettu, 15 min hinnannousu 0,12–0,45 % | −19,03 € | −27,06 € | −15,59 € | −21,26 € | 3 | 0 |
| Vahvistettu, 4 h trendi vanhempaa tasoa ≥1 % | −24,31 € | −41,26 € | +2,35 € | −3,82 € | 3 | 2 |
| Laatufiltteri, korkea volyymi ≥1,6× | −82,19 € | −119,20 € | −94,93 € | −111,02 € | 14 | 2 |

**Yksikään sääntö ei tuottanut voittoa vanhemmalla 90 päivän opetusjaksolla samalla kertaa normaalikuluilla ja kaksinkertaisilla kuluilla.** Siksi **mitään** sääntöä ei valittu automaattiseen käyttöön. Myöhemmän 60 päivän positiivisia lukuja ei saa käyttää valitun mallin tilastollisesti riippumattomana todisteena.

## Tarkasti tunnistetut historialliset voitolliset ostot myöhemmällä 60 päivän vertailujaksolla

| Pvm, FI | Markkina | Sim. osto | +1 % netto myyntitaso | Aika tavoitteeseen | Nettovoitto tilillä | 15 min nousu ennen ostoa | Trendiero 4h vs vanhempi | Volyymi vs 20 kynttilää |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 18.9.2026 11.25 | ETH-EUR | 2 179,11 € | 2 218,58 € | 320 min | +5,45 € | +0,72 % | +1,43 % | 3,51× |
| 21.9.2026 12.30 | BTC-EUR | 73 570,00 € | 74 902,54 € | 300 min | +5,46 € | +0,65 % | +1,09 % | 1,94× |

Nämä esimerkit ovat *jälkikäteen tunnistettuja onnistuneita tapauksia*: vain oston edellä tunnetut tekijät kelpaavat uusien sääntöjen syötteiksi. Voiton toteutumista ei voi tietää ostohetkellä. Kurssin nousu bruttohintana oli noin 1,81 %:n suuruusluokkaa, ja kulumallilla myyty osuus tuotti +1 % ennen henkilöveroja.

## Vastapainoksi ei-onnistuneita ostoesimerkkejä

- 24.8.2026 15.55 BTC-EUR 67 793 € → stop 50 min kuluttua, −12,50 €. Trendiero +0,94 %, volyymi 2,30×, mutta signaalikynttilän sulkeminen suhteessa kynttilän hintahaarukkaan oli heikompi (runko +0,21 %). Suuri volyymi ei yksin riittänyt.
- 30.9.2026 15.55 ETH-EUR 2 407 € → stop 45 min kuluttua, −12,47 €. Trendiero +0,59 %, volyymi 1,28×.
- 15.10.2026 18.40 ETH-EUR 2 176,54 € → iltasulku, −2,73 €. Trendiero +0,30 %.
- 22.9.2026 18.45 BTC-EUR 75 697 € → iltasulku, −4,85 €. Trendiero +0,90 %, volyymi 1,29×.
- 27.8.2026 12.20 BTC-EUR 68 735 € → iltasulku, −4,56 €. Trendiero +0,35 %, volyymi 1,67×.
- 21.10.2026 16.05 ETH-EUR 2 210,82 € → iltasulku, **+0,55 €**. Ei +1 % tavoite, mutta hieman voitollinen sulku, joten tätä ei pidä luokitella nettotappioksi.

## Mahdollinen uusi hypoteesi tutkimukseen, ei käyttöönottoon

Tämän *jälkikäteen* tarkastellun aineiston perusteella kannattaa tulevassa aidosti uudessa testissä kokeilla:
- ostot vain klo **09–14** Suomen aikaa;
- BTC:n tai ETH:n 20/50/100 nouseva trendi ja aiempi laatufiltteri;
- vahvistettu 15 min nousu noin **0,12–0,90 %**, kolme peräkkäistä nousevaa sulkuhintaa;
- vahvempi 4 h trendi ≥ **1 %** suhteessa vanhempaan tasoon;
- poikkeuksellinen volyymi vähintään noin **1,9-kertainen** verrattuna edelliseen 20 kynttilään;
- ei reagoida kesken olevaan kynttilään; ostoa vasta seuraavan 5 minuutin avauksessa.

**HUOM.: nämä viimeiset 1 % / 1,9× rajat ovat juuri tarkastelluista kahdesta onnistuneesta esimerkistä jälkikäteen johdettuja, eivät itsenäisesti validoituja kauppasääntöjä.** Yhdistelmän esiintymistiheys ja kannattavuus vaativat erillisen tulevaisuuteen kulkevan paperitestin. Kahdesta onnistuneesta kaupasta ei voi estimoida luotettavaa osumistodennäköisyyttä.

## Rajoitukset

- Viiden minuutin OHLC-kynttilän `high`-hinnan koskettaminen ei takaa toteutunutta myyntitoimeksiantoa. Todelliseen välittömään kotiutukseen tarvitaan toimeksiantojen ja täyttöjen käsittely pörssissä.
- Pörssipalkkio ja slippage arvioitu kumpaankin suuntaan. Suomen henkilökohtainen luovutusvoittovero puuttuu.
- Samassa kynttilässä stop ja tavoite: simulaatio olettaa stopin toteutuvan ensin.
- Katkojen kohdalla sijainti nollataan ja avoimet positiot likvidoidaan tutkimuksen oletushintaan. Tämä vaikuttaa tulokseen.
- **1 % onnistuneelta kaupalta ei ole 1 % salkusta päivittäin.** Kauppaa ei tehdä joka päivä.
- Kaikki työ tutkimushaarassa/PR-luonnoksessa, ei oikeaa kaupankäyntiä eikä muutosta aiempaan Momentum E -paperisalkkuun.
