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

## Edullisemmat välittäjät – 17.10.2026 valitut ehdokkaat

**Osakkeet ja ETF:t: Trading 212 Invest.** EUR-noteeratuilla tuotteilla välityspalkkio 0 €, mutta kurssiero ja mahdolliset viranomaismaksut eivät häviä. Muun valuutan instrumenteissa 0,15 % FX-maksu oston ja myynnin yhteydessä. Virallinen API on beta-vaiheessa; Trading 212 tukee demo- ja live-ympäristöjä, ja API:n toimeksiannot ovat rajoitettuja tilin päävaluuttaan. **Tässä projektissa vain demo-tilin saldoa lukeva GET-adapteri**, jonka tunnukset annetaan paikallisesti ympäristömuuttujina `TRADING212_DEMO_KEY` / `TRADING212_DEMO_SECRET`. Oikeita tai demotoimeksiantoja ei tehdä.

**Kryptot: Bitvavo.** Julkisesta markkinadatarajapinnasta voi hakea BTC-EUR-, ETH-EUR- ja SOL-EUR-päiväkynttilät ilman tunnuksia. Tämä ei edellytä Bitvavo-tilin avaamista eikä anna toimeksianto-oikeuksia. Kaupankäyntikulut ovat erillinen kysymys ja ne täytyy varmistaa tilikohtaisesti; strategiasimulaation nykyiset kuluoletukset ovat vielä alustavia.

### Julkisen kryptomarkkinan lukutesti iPhonella

[Bitvavon lukutesti GitHub Actionsissa](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/market-scan.yml)

Avaa `Run workflow` → `Run workflow`. Testi hakee tuoreet **valmiit** EUR-päiväkynttilät Bitvavolta ja tulostaa ehdolliset `BUY` / `HOLD`-signaalit pelkkinä tutkimuslukemina. GitHub Actions on hetkellinen testiajoympäristö, ei kaupankäyntipalvelimen 24/7-korvike. Erillinen osakeskanneri vaatii luotettavan datalähteen varmistuksen.

### Tietoturvarajaus

**Älä koskaan lähetä kaupankäyntitilisi salasanoja, API-avaimia tai salaisuuksia ChatGPT-viestinä tai vie niitä julkiseen GitHub-koodiin.** Kun demoavain on ajankohtainen, sen voi lisätä yksityisen kehitysympäristön salaisuushallintaan. Myös automaattisten toimeksiantojen toteutus tarvitsee erillisen lupapäätöksen, käyttöoikeusrajaukset ja testatun täsmäytyksen, jotta uudelleenyritys ei tee tuplaostoa.

Viralliset docs: https://docs.trading212.com/api ja https://docs.bitvavo.com/docs/rest-api/get-candlestick-data/


## iPhone-verkkonäkymä (paperisalkku)

Lähdetiedostot: [docs/index.html](docs/index.html), julkinen [docs/data.json](docs/data.json).
Raportti päivittyy automaattisesti päivittäin noin klo 04.17 UTC (GitHub Actionsin aikataulu voi viivästyä). Tarvittaessa voit myös käynnistää
[Update iPhone paper dashboard](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/dashboard.yml)
→ **Run workflow** → **Run workflow**, jolloin haetaan julkiset kurssit ja päivitetään JSON-tiedosto.

Jotta saat verkkosivun Safariin:

1. Avaa [Repository Settings → Pages](https://github.com/jaheinone-lang/swing-bot-iphone/settings/pages).
2. Valitse **Build and deployment → Source: Deploy from a branch**.
3. Valitse **Branch: main**, kansio **/docs**, ja **Save**.
4. Odota GitHubin ilmoittamaa julkaisuosoitetta. Oletusosoite on
   `https://jaheinone-lang.github.io/swing-bot-iphone/` – linkki ei ole toimiva ennen kuin Pages-julkaisu on valmistunut.
5. Lisää toimiva sivu iPhonen Safari-valikosta kohtaan **Lisää Koti-valikkoon**.

Huomautus: GitHub Actionsin `GITHUB_TOKEN`-commitit eivät välttämättä käynnistä Pagesin branch-julkaisua uudelleen. Siksi staattinen sivu hakee ensisijaisesti uusimman julkisen JSON-raportin suoraan GitHubin raw-tiedostosta ja käyttää Pagesin kopiota vain varavaihtoehtona. Raportin ajastettu GitHub Actions -ajo voi joskus viivästyä tai epäonnistua, ja GitHubin välimuistit voivat aiheuttaa viivettä. Sivun päiväys ja vanhentumismerkintä kertovat, milloin data on päivitetty.

iPhone-näkymä käyttää SAP.DE-osakkeelle **epävirallista Yahoo Finance -historiadataa**, jonka EUR-valuutta, päivämäärät ja ajantasaisuus tarkistetaan ennen näyttämistä. Erillinen CLI käyttää edelleen Stooqia, joka saattaa vaatia API-avaimen. Jos osake- tai kryptosyöte ei vastaa, **osakekurssi tai yhdistetty tuottosimulaatio näytetään puuttuvana**. Bitvavon kryptodata toimii ilman tiliä. Historiallinen tuottosimulaatio perustuu useisiin oletuksiin eikä ole validoitu sijoitusstrategia. Tämä on tutkimusnäkymä, ei käyttäjän oikea salkku.


## Jatkuva viiveellinen paperisalkku (lisätty 17.10.2026)

iPhone-sivu näyttää nyt **kaksi eri laskentaa**:

- **Historiallinen backtest**: jälkikäteen simuloitu tuotto vanhasta hintadatasta. Tulokset eivät ole toteutuneita tai tulevaisuuden ennusteita.
- **Jatkuva paperisalkku**: **uusi 5 000 € fiktiivinen tili ilman takautuvia täyttöjä**. Tilatiedosto `paper/state.json` säilyttää käteisen, avoimet positiot, stopit, signaalit, päiväkohtaiset salkkuarvot ja simuloitujen kauppojen tapahtumat. Julkinen, suppeampi kooste näkyy `docs/data.json`-tiedostossa.

Paperisalkku alustui 16.10.2026 valmistuneeseen dataan, lähtöarvo 5 000 €. Samasta päivästä uudelleen ajaminen **ei tee samoja ostoja kahdesti**. Ostoehto muodostetaan sulkeutuneesta päiväkynttilästä ja mahdollinen paperiosto kirjautuu vasta **seuraavan markkinapäivän kynttilän valmistuttua** käyttäen sen avaushintaa ja oletuskuluja. Näin kyse on **viiveellisestä forward-simulaatiosta, ei ajantasaisesta demo-toimeksiantojen toteutuksesta**. Kryptot päivittyvät myös viikonloppuna, osakkeet vain pörssipäivinä.

Päivitys epäonnistuneen tai puuttuvan hintasyötteen aikana **ei nollaa** salkkua eikä keksi uusia kauppoja. Yli viikon viive vaatii tilan tarkistusta käsin. Uudet ostot pysähtyvät salkun arvonlaskun saavuttaessa 25 %, mutta toteutuva tappio voi olla suurempi, eikä tämä ole sijoituspääoman suoja.

Läpinäkyvyys: molemmat tietotiedostot ovat **julkisessa GitHub-repositoriossa**; ne sisältävät vain fiktiivisen salkun. Älä lisää oikeita tilisaldoja, käyttäjätietoja, salasanoja tai kaupankäyntiavaimia näihin tiedostoihin.

Päivittäin ajastettu [raporttipäivitys](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/dashboard.yml) hakee hintatiedot ja validoi ohjelmakoodin ennen paperitilin käsittelyä. GitHub Actions -aikataulu on parhaansa yrittävä ja voi viivästyä. Viimeisin tarkistettu raporttipäivä näkyy sovelluksessa. Testit: `python -m unittest discover -s tests -v`; myös iPhone-sivun JavaScriptin syntaksi tarkistetaan.
