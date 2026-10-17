# Swing Bot iPhone — yhdistetty osake- ja kryptobotti

**Tila: TURVALLINEN TESTIVERSIO.** Ei oikeaa rahaa, ei API-kaupankäyntiavaimia, ei osto-/myyntitoimeksiantoja. Yhteinen 5 000 € simuloitu salkku.

## Markkinat

- **Osakkeet/ETF:t:** EUR-noteeratut saksalaisen pörssin (`.DE`) instrumentit Stooq-päivädatasta. Esimerkki: `SAP.DE`. Symbolien valuutta ja noteerauspaikka on tarkistettava erikseen.
- **Kryptot:** Krakenin julkiset europarit `XBTEUR`, `ETHEUR` (myös `SOLEUR` tuettu).
- Osakkeet ovat tyypillisesti kaupankäynnissä vain pörssipäivinä, kryptot joka päivä.
- **Älä sekoita USD-, NOK- tai GBP-kursseja euromääräiseen simulaatioon ilman oikeaa valuuttamuunnosta.** Tässä versiossa käytetään vain EUR-merkintöjä.

## Strategia

- Signaali syntyy *päättyneen päivän sulkeutumisen jälkeen*: 20 päivän päätöskurssin ylitys sekä 50 päivän trendisuodatin.
- Testi simuloi ostoa **seuraavan saatavilla olevan päivän avauksessa** (ei tiedossa olleella signaalipäivän hinnalla).
- Long-only; 1 % salkkuriski/kauppa laskennallisena position mitoituksena, enintään 20 % salkusta yhteen instrumenttiin.
- ATR(14) x 2 määrittää stopin; sijoituksen avoin stop voi kiristyä päätöshintojen perusteella.
- Pörssiosakkeille käytetään kokonaisia osakkeita; kryptolle desimaalikappalemääriä.
- Arvioidut kulut + slippage: osakkeet 0,10 % + 0,05 % / suunta, kryptot 0,40 % + 0,15 % / suunta. **Nämä ovat oletuksia, eivät toteutuneita välittäjäkuluja.**
- Kun simuloidun salkun lasku huipusta on >= 25 %, **uudet ostot jäädytetään pysyvästi tässä ajossa**. Jo omistetut positiot käsitellään stopien kautta; toteutuneet tappiot voivat olla yli 25 % etenkin nopeassa kurssiromahduksessa.
- Malli ei vielä huomioi veroja, korkoja, osinkoja, yhtiötapahtumia, kaupankäyntirajoituksia, minimitoimeksiantokuluja eikä kaikkia spreadin ja markkinaliikenteen vaihteluita.

## Aja testit ilman asennuksia iPhonella

[Katso GitHub Actionsin viimeisimmät testiajot](https://github.com/jaheinone-lang/swing-bot-iphone/actions). Avaa `Python safety tests` → onnistunut suoritus → `unit-tests`. Testiajo tulostaa synteettisellä osake- ja kryptodatalla tehdyn simulaation.

### Oman kehitysympäristön komennot (Python 3.11+)

```bash
python -m unittest discover -s tests -v
python -m swingbot.multi_cli --mode demo --summary-only
python -m swingbot.multi_cli --mode live --summary-only
```

`demo`: **keinotekoinen hintadata** – tuotot eivät ole historiallisia eivätkä ennusteita.

`live`: historiakynttilät Krakenilta ja Stooqilta; tämä on yhä **vain offline-backtest**, ei live-kaupankäynti. Stooq voi vaatia rekisteröitävän `STOOQ_API_KEY`-avaimen. Jos Stooq tai Kraken ei vastaa, ajo **epäonnistuu**, eikä sen tilalle näytetä keksittyjä hintoja.

Esimerkki avaimesta vain kehitysympäristössä: `export STOOQ_API_KEY='...'` – ei ikinä GitHubiin tai julkisiin tiedostoihin. Krakenin julkiseen dataan ei tarvita kaupankäyntiavaimia.

Krakenin julkisesta OHLC-rajapinnasta saadaan vain viimeisimmät noin 720 kynttilää; keskeneräinen kynttilä jätetään pois. Historialliset datasyötteet voivat olla puutteellisia, ja eri pörssien päivän sulkeutumisajat poikkeavat toisistaan.

## Mitä puuttuu ennen oikeaa kaupankäyntiä?

1. Varmennettu ja valvottu historiallinen markkinadata, valuuttakäsittely ja osakkeiden yhtiötapahtumakorjaukset.
2. Kunnollinen käyntiaikainen backtest, ulkopuolisen ajanjakson validointi ja paperikaupankäynti.
3. Todelliset kulut, minimipalkkiot, likviditeetti ja verovaikutukset.
4. Välittäjäkohtaiset API-kytkennät, toimeksiantojen täsmäytys, vikasietoisuus, käyttöoikeudet, salaisuuksien hallinta ja hälytykset.
5. Erillinen käyttäjän hyväksyntä ennen oikeaa kaupankäyntiä.

**GitHub-projekti on julkinen. Älä lisää siihen API-avaimia, salasanoja tai henkilötietoja.**
