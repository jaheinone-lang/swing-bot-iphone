# Swing Bot: 100 % vuositavoite ja 200 €/kk pitosalkku

**Toteutus:** pelkkä read-only tutkimus, ei siirtoja eikä oikeita kauppoja.

**Varmennettu testiajo:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/43287590867

## Pääomat
- Treidaus: erillinen 5000 € tutkimussalkku, ei vipua. 100 %:n vuotuinen nettotuotto on erittäin aggressiivinen **tavoite**, ei ennuste eikä automaattinen riskin korotus. 5000 euron kaksinkertaistaminen 10000 euroon vaatisi 5000 euroa sijoitustuottoa ilman talletuksia.
- Pitosalkku: alkaa nollasta, ulkoinen 200 €/kk, simulaatiossa 50 % BTC-EUR ja 50 % ETH-EUR. Painojakauma on alustava ja muutettavissa. Osto vasta kuukauden ensimmäisellä käytettävissä olevalla UTC-päiväkynttilän OPEN-hinnalla.
- Omia talletuksia ei koskaan lasketa tuotoksi. Pitosalkkua ei käytetä treidauksen tappioiden kattamiseen.
- Erillinen vanha E-paperiseuranta pysyy ennallaan. Tavoitteen asettaminen ei laukaise oikeita ostoja.

## Varmennettu 200 €/kk pitosalkun BTC/ETH-simulaatio

| Jakso | Kuukausia | Talletettu | Loppuarvo arvioidun loppumyynnin kulujen jälkeen | Nettovoitto/tappio | 2x kuluilla nettovoitto/tappio |
|---|---:|---:|---:|---:|---:|
| 2021-10-23–2023-12-31 | 27 | 5400 € | 6988,49 € | +1588,49 € | katso JSON-testiraportti |
| 2024-01-01–2026-10-22 | 34 | 6800 € | 6745,17 € | −54,83 € | −108,58 € |

Jaksojen pääomat alkavat erikseen nollasta; eivät ole jatkumo. Osto- ja myyntikulut simuloitu, verot jätetty pois. Historiallinen markkinahinnan kehitys ei ole tuleva tuottolupaus.

## Vertailu päivänsisäiseen kaupankäyntiin

55 päivän päiväkynttilä-breakout 5000 €:n treidaussalkulle oli 2024–2026 +129,21 € (kaksinkertaisilla kuluilla +88,53 €), mutta 2021–2023 −59,12 €. Passiivinen 20 % BTC/ETH + 80 % käteinen -verrokki voitti sen molemmilla aikakausilla. Pitosalkun talletuksia ei saa summata aktiivisen mallin tuotoksi.

## Riskit ja hyväksyntä

Raportoi erikseen (1) ulkoiset talletukset, (2) sijoitusten todellinen muutos, (3) transaktiokulut, (4) verot, (5) aikapainotettu tuotto sekä salkun maksimiarvonlasku. Treidausmallissa 20 % maksimipositio ja 0,25 % nimellinen stop-riski per kauppa ovat ennallaan; ne eivät takaa rajattua todellista tappiota. Vipu ja automaattinen riskin nostaminen poistettu.

100 %:n vuositavoite on vain mittari. Se ei oikeuta strategiaa live-käyttöön ilman riippumatonta lukittua forward-only-paperitestiä ja toimeksiantojen todellisten kulujen mittausta.

## Tutkimuskoodi

- swingbot/monthly_hold_research.py
- tests/test_monthly_hold_research.py
- .github/workflows/crypto-daily-swing.yml

GitHub Actions julkaisee erillisen MONTHLY_HOLD_VERIFIED_RESULT-tuloksen; yksikään näistä ei tee oikeita toimeksiantoja.
