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


## Tutkimusvertailu: Swing Bot vs. osta ja pidä (17.10.2026)

iPhone-sovellus näyttää nyt molempien menetelmien **historiallisen kokonaistuoton, CAGR-vuosituoton, suurimman arvonlaskun, volatiliteetin sekä Sharpen luvun (0 % riskitön korko)**. Lisäksi näkyy viimeisten 180 päivän erittely. Vertailu on tutkimusta eikä anna kaupankäyntikäskyjä.

Vertailu käyttää täsmälleen samoja EUR-hintapäiviä ja samaa 5 000 € lähtöpääomaa. Osta ja pidä hajauttaa summan neljään instrumenttiin yhtä suurella euromäärällä 51 havaintokynttilän lämmittelyn jälkeen, seuraavien avauskurssien perusteella. Laskennassa sallitaan osakkeille vain kokonaiskappaleet, kryptolle 8 desimaalia, eikä salkkua tasapainoteta uudelleen. Historiallinen Swing Bot käyttää samaa kulumallia: **osakkeet 0 bps välityspalkkio + 5 bps slippage, kryptot 25 bps palkkio + 15 bps slippage suuntaansa**. Osta ja pidä -vertailun kassavaroista vähennetään ostokulut, mutta lopullisten positioiden likvidointikuluja ei ole huomioitu. Kuluoletukset ovat tutkimusarvioita eivätkä kaupankäyntipalveluiden sitovia tarjouksia.

Tärkeää: **ostettu ja koko ajan sijoitettuna pidetty salkku kantaa enemmän markkinariskiä** kuin strategia, joka usein pitää käteistä. Tästä syystä tuottojen ero ei suoraan osoita parempaa riskikorjattua sijoitusmenetelmää. Osta ja pidä -vertailu on vain yksi vertailupohja eikä itsessään sijoitussuositus. Yhtiötapahtumat, osingot, delistaukset, maksuerot, valuuttariskit, verotus ja kaupankäyntikelpoisuus voivat vääristää molempia tuloksia. **Viimeisten 180 päivän osuus ei ole riippumaton tulevaisuustesti**, koska malli on jo kehitetty samoja historiallisia hintoja tarkastelemalla.

Sharpen luku annualisoidaan 365 päivän perusteella päivätuottojen keskihajonnasta. Osakkeiden sulkeutuneina päivinä käytetään edellistä tunnettua päätöshintaa. Tämä ei mittaa todellista päivänsisäistä riskiä, ja epäsynkroniset pörssipäivät voivat vääristää lukuja. Vasta pidempi ilman jälkikäteen tehtyjä sääntömuutoksia suoritettu paperijakso antaa luotettavampaa näyttöä mallin toiminnasta.


## Strategialaboratorio 4.0 (17.10.2026)

**Tämä on erillinen historiallinen tutkimus.** Jatkuva paperisalkku jatkaa nykyisillä säännöillään eikä oppiminen muuta sen kauppoja tai käytä oikeaa rahaa.

Kolme etukäteen määriteltyä versiota:

| Versio | Läpimurto | Trendi | Stop | Positioraja | 200 päivän filtteri | Momentum-ranking | Aikapoistuminen |
|---|---:|---:|---:|---:|---|---|---|
| A – Nykyinen | 20 | 50 | 2,0 ATR | 20 % | ei | ei | ei |
| B – Nopeampi | 15 | 50 | 2,5 ATR | 25 % | kyllä | 2 parhainta signaalia | 20 kynttilää ilman +2 % nousua |
| C – Aggressiivinen | 10 | 30 | 3,0 ATR | 30 % | kyllä | 2 parhainta signaalia | 15 kynttilää ilman +2 % nousua |

Kaikissa 1 % laskennallinen positioriski, *vain long*, seuraavan täyden päiväkynttilän avaukseen sijoitetut historialliset täytöt, arvioidut Bitvavon/Trading 212:n kaupankäyntikulut ja -liukuma, sekä 25 % laskuun pysäyttävä uusien ostojen kielto. Kurssihypyt voivat aiheuttaa yli 25 % tappion, koska stop ei takaa toteutushintaa. 200 päivän filtteri tarkoittaa, että päätöskurssi on viimeisten 200 päätöskurssin keskiarvon yläpuolella (ei kahden keskiarvon risteämää). Momentum perustuu 60 kynttilän tuottoon. Aikapoistuminen pannaan täytäntöön vasta seuraavan avauksen kautta.

### Korkoa korolle ja vero

**Uudet sijoituskoot lasketaan joka kaupalle uudestaan salkun senhetkisestä verovarauksen jälkeisestä arvosta.** Sijoitusrahat kasvavat voitoista ja pienenevät tappioista. Malli kohdistaa yhden ostolotin kerrallaan instrumenttia kohti, joten luovutusten kustannusperuste on yksiselitteinen ilman avoimien eri-ikäisten FIFO-lottien yhteensovitusta.

Veroarvio perustuu oletukseen: **Suomessa verotettava yksityishenkilö**, 30 % pääomatulon osuudesta 30 000 euroon asti ja 34 % ylittävältä osalta. Veroa varataan EUR-määräisistä **realisoiduista myyntivoitoista**, hankinta- ja luovutuskulujen jälkeen; realisoituneet tappiot vähennetään verovuoden voitoista ja ylijäävä osuus yksinkertaistetusti enintään viiden seuraavan vuoden voitoista. Kasvanut laskennallinen verovaraus vähentää ostamiseen käytettävissä olevaa käteistä, mutta veroa ei oikeasti makseta. **Avoimien positioiden laskennallista veroa ei varata**; loppupääoma on tältä osin vain osittainen verojen jälkeinen luku.

Rajoituksia: muiden henkilökohtaisten pääomatulojen määrä oletetaan nollaksi; todelliset vähennykset, osinkovero, tappioiden käyttö muita pääomatuloja vastaan, alle 1 000 € myynnit, hankintameno-olettama, osakesäästötili, yhteisöverotus, kryptovaihdot, valuuttamuunnokset sekä muu tosiasiallinen verotieto eivät ole mukana. Tämä on **turvallisuutta parantava arvio**, ei verolaskelma tai ohje veroilmoitukseen. Lisätietoja: https://www.vero.fi/henkiloasiakkaat/verokortti-ja-veroilmoitus/tulot/paaomatulot/ ja https://www.vero.fi/henkiloasiakkaat/omaisuus/sijoitukset/virtuaalivaluutat/

### Historiasta oppiminen ilman tulevaisuustietoa

Jokainen kolmesta kiinteästä strategiasta testataan samalla EUR-historialla. Data jaetaan ajallisesti ensimmäiseen 65 % kehitysjaksoon ja viimeiseen 35 % myöhempään arviointijaksoon. **Kehitysjaksolla** pisteet muodostuvat kaavalla: tuotto %-yksikköä miinus 1,5 × suurin arvonlasku %-yksikköä. Vain kehitysjaksolla parhaiten pisteytettyä mallia tarkastellaan seuraavaksi myöhemmällä jaksolla. **Testitulokset eivät automaattisesti muuta tuotannossa olevaa paperisalkkua, eivätkä johda oikeisiin toimeksiantoihin.**

Koska näitä strategioita on jo ajateltu historiallisten tulosten perusteella, myöhempää testijaksoa ei voi pitää täysin riippumattomana todistuksena. Todellinen uusi ulkopuolinen data kertyy vasta tulevilla päivillä lukittujen sääntöjen jälkeen. Pelkkä takaisin testattu vuosituotto ei kerro riittävästi; myös kulut, voittojen kesto, riskikorjattu tuotto, arvonlasku, kaupankäyntitiheys ja verovaraus on tarkasteltava.

**Data:** Kryptot Bitvavon julkisista EUR-päiväkynttilöistä ja SAP.DE epävirallisesta Yahoo Finance -rajapinnasta. Hintojen ajantasaisuus ja noteerausvaluutta tarkistetaan syötteissä, mutta osinkojen, osakesplittien, yhtiötapahtumien ja muiden datavirheiden täydellistä korjausta ei ole. Ensimmäisessä analyysissä on vain neljä instrumenttia ja noin kaksi vuotta historiaa; luotettava mallin optimointi edellyttää enemmän ajallista vaihtelua, muita osakkeita ja instrumentteja sekä pitkää uutta paperikauppajaksoa.

Aja testit: `python -m unittest discover -s tests -v`. Ei API-kaupankäyntiavaimia, ei toimeksiantoja.


### Jatkuvan paperisalkun verovaraus (lisätty)

Myös `paper/state.json` sisältää nyt arviot `tax_reserved_eur` ja `disposals`: simuloidun myynnin yhteydessä kirjataan verotettava EUR-voitto tai -tappio täysimääräiseen hankinta- ja myyntikuluun perustuen. Uudet positiot mitoitetaan **salkun arvosta vähennetyn verovarauksen** ja **kassan verovarauksesta vapaan osuuden** mukaan. Bruttokäteinen ei muutu varauksen takia, mutta osa siitä on laskennallisesti lukittu pois kaupankäynnistä. Paperisalkun näkymä näyttää sekä varauksen että uudelleensijoitettavissa olevan käteisen.

Vanhan `paper/state.json`-muodon kertaluonteinen muunnos sallitaan vain, kun tilillä ei ole vanhoja kauppoja tai positioita. Jos vanhaa kaupankäyntihistoriaa on, päivitys pysähtyy ja vaatii manuaalisen verokirjanpidon tarkistuksen; mitään ei nollata tai lasketa arvaamalla. Sama koskee myöhempiä epäluotettavia hintasyötteitä.

**Verovaraus ei vastaa maksettua veroa eikä täydellistä tulevan veron määrää:** avoimet voitot, muut pääomatulot, osingot, 1000 € luovutussääntö, hankintameno-olettama, vaihtoehtoiset tilimuodot ja yhtiön kautta sijoittaminen vaativat erillisen mallin. Tämä on henkilön EUR-arvopaperien ja spot-kryptojen tutkimuskäyttöä; ei johdannaisia tai lainoitusta.
