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

**Osakkeet ja ETF:t: Trading 212 Invest.** EUR-noteeratuilla tuotteilla välityspalkkio 0 €, mutta kurssiero ja mahdolliset viranomaismaksut eivät häviä. Muun valuutan instrumenteissa 0,15 % FX-maksu oston ja myynnin yhteydessä. Virallinen API on beta-vaiheessa; Trading 212 tukee demo- ja live-ympäristöjä, ja API:n toimeksiannot ovat rajoitettuja tilin päävaluuttaan. **Tässä projektissa vain demo-tilin Metadata-luetteloa lukeva GET-sovitin ja erillinen kokeellinen saldo-sovitin (ei käytössä tässä yhteydessä)**, jonka tunnukset annetaan paikallisesti ympäristömuuttujina `TRADING212_DEMO_KEY` / `TRADING212_DEMO_SECRET`. Oikeita tai demotoimeksiantoja ei tehdä.

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


## Veroprofiili lukittu: henkilökohtainen sijoittaminen Suomessa

Käyttäjän päätöksen perusteella Swing Bot käyttää jatkossa lähtökohtana Suomen verotuksessa yksityishenkilön henkilökohtaista sijoitussalkkua. Paperitili tallentaa veromallin `PERSONAL_FINLAND_ESTIMATE`, eikä siirtoa holding-yhtiöön ole mahdollista tehdä automaattisesti (`NO_AUTO_HOLDING_TRANSFER`).

Tällä hetkellä ohjelma mallintaa pääomatuloveron 30 % ensimmäisiin 30 000 euroon asti ja 34 % ylimenevältä osalta; hankinta- ja myyntikulut, realisoidut EUR-myyntivoitot ja tappiot sekä yksinkertaistetun viiden seuraavan vuoden tappionsiirron. Todellisia muita pääomatuloja, alle 1 000 euron luovutusten erityissäännöksiä, osinkoja, arvo-osuustilien monilottista FIFOa tai hankintameno-olettamaa ei mallinneta täydellisesti. **Verovaraus on vain tutkimusarvio**, ei lopullinen verotuspäätös.

Jos sijoittaminen myöhemmin tehdään holding-yhtiön kautta, kyseessä on uusi erillinen oikeudellinen sijoittaja, kirjanpito ja verotus. Henkilökohtaisesti omistettujen osakkeiden siirtäminen osakeyhtiöön apporttina on yleensä luovutus käyvästä arvosta ja voi aiheuttaa yksityishenkilön luovutusvoiton. Yhtiöön voidaan tulevaisuudessa sijoittaa erikseen uusia varoja, mutta olemassa olevan salkun arvopapereiden siirtoa ei saa käsitellä automaattisena verottomana tilisiirtona. Lopullinen järjestely kannattaa tarkistaa veroasiantuntijan kanssa ennen tekemistä.

Lähteet: [Verohallinto — pääomatulot](https://www.vero.fi/henkiloasiakkaat/verokortti-ja-veroilmoitus/tulot/paaomatulot/), [Verohallinto — apportti](https://www.vero.fi/syventavat-vero-ohjeet/ohje-hakusivu/48935/omaisuuden-luovutusvoitot-ja-tappiot-luonnollisen-henkilon-tuloverotuksessa4/) ja [Verohallinto — osakkeiden myynti](https://www.vero.fi/henkiloasiakkaat/omaisuus/sijoitukset/osakkeiden_myynt/).


## 5.0 Osakkeiden/ETF:ien laajamittainen seulonta ja listautumiset

**Tila 18.10.2026:** Trading 212 Invest Practice -tilin Metadata-only API -yhteys vahvistettu GitHub Actions -testissä: 10 372 osakeinstrumenttia ja 6 749 ETF-instrumenttia (17 121 yhteensä). Erillistä 200+ kaupankäyntipäivän varmennettua hinta-/volyymisyötettä ei vielä ole, joten TOP 20 -rankingiin tai osakepaperikauppoihin ei näiden lukumäärien perusteella siirrytä. Tähän julkiseen GitHub-repositorioon **ei koskaan viedä avaimia, raakoja asiakkaan tilitietoja, kaupankäyntihistoriaa tai tilikohtaista täydellistä metadataa**.

### Datalähteet ja valvonta

- Trading 212 virallinen `GET /api/v0/equity/metadata/instruments` palauttaa tilillä kaupankäyntiin saatavilla olevien instrumenttien valikoiman. `swingbot/trading212_universe.py` osaa hakea sen DEMO-ympäristöstä ja tehdä vain lukumääräyhteenvedon; avain tulee turvallisesta ympäristömuuttujasta, jota ei tulosteta. Metadatassa on muun muassa instrumentin ISIN, ticker, valuutta, osake/ETF-laji, `addedOn` ja markkina-aikataulun tunnus. Endpointin rajoitus 1 kysely/50 s. Pörssin varsinainen IPO-päivä **ei ole** `addedOn`. Lisätieto: https://docs.trading212.com/api/instruments/instruments.
- SEC EDGAR `companyfacts` (`swingbot/sec_fundamentals.py`) käsittelee yhdysvaltalaisten raportoijien US-GAAP-tilinpäätöstietoja vain alkuperäisen **julkistamis-/filing-päivän** jälkeen. Liikevaihdon kasvu, nettotulos, liiketoiminnan kassavirta ja investointien jälkeisen vapaan kassavirran arvio ovat käytettävissä silloin, kun relevantit faktat löytyvät; puuttuvaa lukua ei arvata. SEC ei anna analyytikkojen konsensusennusteita eikä suoraan todellisia "earnings surprise" -lukemia. SEC API:n käytölle tarvitaan oikea tunnistettava käyttäjäagentti ja yhteystieto, jota ei lisätä julkiseen repoosi. Lisätieto: https://www.sec.gov/search-filings/edgar-application-programming-interfaces.
- Päiväkohtaisille hinta-, volyymi-, oikaistu yritystapahtuma- sekä valuuttatiedoille tarvitaan erillinen lisensoitu tietolähde. Mahdollinen laajan maailman EOD-datan toimittaja: EODHD `EOD Historical Data — All World` (alkaen 19,99 USD/kk listahinnan mukaan 17.10.2026). Ennen tilausta tulee varmistaa käyttöoikeus, palautettavat ETF-/delistatut instrumentit ja markkinakohtaiset kattavuudet. Markkinadataa ei saa kopioida julkiselle GitHub Pages -sivulle ilman toimittajan lupaa.
- IPO-havainnointi (`swingbot/ipo_watch.py`) vaatii vahvistetun kaupankäynnin ensimmäisen päivän, vähintään viisi valmistunutta istuntoa, aidon OHLCV-sarjan, mitatun spreadin, riittävän vaihdon, valuuttamuunnoksen ja Trading 212 -tilin instrumenttisaatavuuden ennen kuin edes harkitaan simuloitua strategiaa. Se **ei osta ensimmäisen päivän IPO-huumassa**. Säännöt: suhteellinen vaihto ≥1,2 × aiempien viiden päivän mediaani, päivittäinen vaihto vähintään viiden miljoonan yksikköä noteerausvaluutassa, spread ≤40 bps, avausgappi korkeintaan 12 %, 5 päivän huipun läpimurto. Kaikki signaalit ovat vain seurantalistan tapahtumia, eivät toimeksiantoja.
- Osake-/ETF-seula (`swingbot/equity_screen.py`): ≥201 valmistunutta havaintoa, yhtiötapahtumien oikaisu, EUR-valuutta ja alle 7 päivän tiedon ikä, mitattu spread ≤40 bps, 20 päivän mediaanivaihto ≥2 miljoonaa EUR, 50 päivän trendi > 200 päivän trendi, 20 päivän huipun läpimurto, 60 päivän momentum ja 14 päivän ATR. Osaketutkimuksessa voidaan lisätä vain ajallisesti oikein saataville tulleet SEC:n faktat. ETF-analyysi on ensisijaisesti momentum-/riski-/kulusääntöinen, ei yhtiön tulos-analyysi. Johdannaiset, CFD:t ja vivutetut tuotteet eivät kuulu tähän seulaan.
- **Varoitus:** koko välittäjävalikoiman lista ei vielä tarkoita, että kaikille symboleille olisi laillisesti käyttökelpoinen lisensoitu markkinadata; käsittelemättömät tai väärään ISINiin yhdistetyt rivit jätetään tutkimuksen ulkopuolelle. Tässä vaiheessa tutkimussäännöt on validoitu *keinotekoisilla testihavainnoilla*, ei koko Trading 212 -salkkuvalikoiman aidolla backtestillä.

### Ensimmäiset lähdepohjaiset IPO-esimerkit

Tiedosto [docs/ipo_research.json](docs/ipo_research.json) sisältää 17.10.2026 mennessä vahvistettuja **tutkimuskohteita** (CTY, IAM, ACCV) ja lähteet yritysten sijoittajatiedotteisiin sekä julkisiin Trading 212 -instrumenttisivuihin silloin kun niitä löytyi. Ne eivät ole automaattisia ostosignaaleja eikä tämän tiedoston tietoja ole varmennettu käyttäjän kaupankäyntitililtä. CTY:n 18 USD IPO-merkintähinta ja 22,40 USD ensimmäisen päivän päätöshinta tuottaa 24,44 % *merkintähintaan nähden*, mutta jälkimarkkinoille tullut yksityissijoittaja ei välttämättä päässyt ostamaan merkintähintaan. Vain todellinen jälkimarkkinan osto-/myyntihinta lasketaan strategian tuotoksi.

### Mikä voisi nostaa nettotuottoa?

Kaikki nämä ovat **hypoteeseja**, ei todistettua positiivista alfa-tuottoa:

1. Likvidien yritysten vahva 3–12 kk momentum yhdistettynä 50/200 päivän markkinatrendiin.
2. Tuloksen kasvun ja kassan laadun vahvistus ennen momentum-ostoa; SEC:n tiedot on katsottava oikean filing-päivän mukaan.
3. Tulosjulkistuksen jälkeinen positiivinen uutinen ja markkinareaktio (earnings drift) vain, jos erilliset konsensusennusteet ja luotettava julkistusaika ovat olemassa; muuten malli jätetään pois.
4. IPO-kohteille vasta ensimmäisen 5–10 päivän jälkeen vahvistettu hintataso ja vaihto; aloitetaan enintään pienellä tutkimuspositiolla, ei ensimmäisen päivän "popin" jahtaamista.
5. Väärien signaalien vähentäminen likviditeetti-, spread-, valuutta-, corporate-action- ja tiedon tuoreusrajoituksilla; arvioidaan myös menetetyt voitot, sillä tiukat ehdot voivat vähentää tuottoa.
6. Korkoa korolle vain varojen nykyisen verovarauksen jälkeisestä arvosta ja verojen sekä kustannusten jälkeen. Tarpeetonta kaupankäyntiä vältetään.

Mikään näistä tutkimusmoduuleista **ei muuta nykyisen paperisalkun sääntöjä**, ota käyttöön API:n kauppaoikeuksia tai siirrä varoja. Verrataan eri historiajaksoissa, erillisessä myöhemmässä validoinnissa sekä tulevissa forward-paperitesteissä ennen muutospäätöstä.

**Tietoturva:** API-avaimia ei lähetetä ChatGPT-viesteihin eikä tallenneta julkiseen GitHub-projektiin. Tilikohtaisen tiedon käyttö on rakennettava erilliseen yksityiseen ympäristöön, jossa on vain lukuoikeudet, tarkoituksenmukaiset rajaukset, audit-loki ja käyttöehdoilla sallittu datan käsittely.


## Markkinadatan lähteet valmisteltu ilman Trading 212 -tiliä (17.10.2026)

**Tärkeää:** sovittimien luominen ja offline-testien läpäisy ei tarkoita, että ulkoiset API-yhteydet olisivat oikeasti käytössä tai koko välittäjän instrumenttivalikoima seurannassa. Näiden laajojen markkinoiden tuloksia ei näytetä valmiina BUY-signaaleina.

| Lähde | Tutkimuksen tarkoitus | Tila | Mitä puuttuu |
|---|---|---|---|
| Bitvavo public OHLC | BTC/ETH/SOL EUR-päiväkynttilät | käytössä nykyisessä raportissa | instrumenttikattavuuden laajennus |
| Yahoo epävirallinen | SAP.DE:n EUR-historian vertailu | nykyisessä raportissa, rajoitettu | yritystapahtumat, tuen pysyvyys |
| [EKP:n viitekurssit / Frankfurter v2](https://frankfurter.dev/) | USD/GBP/CHF/NOK/SEK/DKK -> EUR | `swingbot/ecb_fx.py`, offline-testeissä | tuotantovirtaan yhdistäminen, toteutuskurssin tarkistaminen |
| [SEC EDGAR](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | viralliset US-GAAP tilinpäätökset | `swingbot/sec_fundamentals.py` | SEC-tunniste, CIK-yhdistys, datan aikarajaus |
| [SEC ticker/exchange/CIK](https://www.sec.gov/files/company_tickers_exchange.json) | US-yhtiöiden identiteettien yhdistys | `swingbot/sec_identity.py`, offline-testeissä | ticker-/pörssi- ja ISIN-varmistus; ei arvaavaa symbolimuunnosta |
| SEC submissions (S-1/F-1/424B4) | IPO-hakemusten löytyminen | `swingbot/sec_ipo_filings.py`, offline-testeissä | SEC-tunniste, vahvistettu listautumispäivä, toteutunut jälkimarkkinadata |
| [EODHD historical EOD](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) | osakkeiden ja ETF:ien maailmanlaajuinen OHLCV | `swingbot/eodhd_feed.py`, offline-testeissä | oma API-tili, sopiva käyttöoikeus ja split-/osinkooikaisujen tarkistus |
| Trading 212 Invest DEMO metadata | tilikohtainen STOCK-/ETF-universumi | `swingbot/trading212_universe.py`, odottaa | käyttäjän tili ja vain lukuoikeudelliset tunnukset suojattuun ympäristöön |

### Datan laatua koskevat kiellot

- Valuutta ei saa muuttua euroksi pelkällä tickerin nimeämisellä. SEK, GBP ja USD tarvitsevat oikean päiväkohtaisen FX-viitekurssin; verotus ja kaupankäynti vaativat erikseen toteutuneen valuutanvaihtokurssin/kulut.
- ECB-julkaisupäivä saa olla enintään havainnointipäivä, eikä tulevaisuuden kurssia saa käyttää historiassa. Julkinen EKP:n keskikurssi ei ole toteutunut kaupankäynnin FX-kurssi.
- EODHD:n raakaa OHLCV:tä ei julisteta split- tai osinkokorjatuksi automaattisesti. Yhtiötapahtumien oikaisu, delistatut osakkeet ja historiallisen universumin rajaus ovat välttämättömiä kunnolliseen backtestiin.
- Yhtiön SEC-raportin *filed*-päivä on se hetki, jolloin tieto tulee käytettäväksi historialliseen malliin; tilikauden päättymispäivän kohdalle tietoa ei saa siirtää.
- IPO:n S-1/F-1-hakemus ei tarkoita, että osake varmasti listautuu. Trading 212:n `addedOn` ei ole pörssin IPO-päivä. IPO-merkintähinta ei välttämättä ole yksityissijoittajan toteutettavissa.
- Symbolia/ISINiä/CIKiä ei yhdistetä arvauksen, samankaltaisen nimen tai valuuttamismatchin perusteella.
- Markkinadataa ei tallenneta julkiselle GitHub Pages -sivulle ilman toimittajan lupaa. SEC:n julkinen tieto ja kaupallisesti lisensoitu EODHD-data käsitellään eri tavoin.

### Kun Trading 212 -tili on avattu

1. Tilin ja Invest/DEMO-vaihtoehdon vahvistaminen. Aluksi ei talletusta eikä oikeita kauppoja.
2. Vain lukuoikeudellinen tilikohtaisen instrumenttilistan haku erillisessä salaisuuksia suojaavassa ympäristössä. Salaisuuksia ei lähetetä ChatGPT-keskusteluun, julkaista GitHubiin tai lisätä selainkoodiin.
3. Tunnisteiden, ISINien, pörssin ja noteerausvaluuttojen yhdistäminen SEC:iin/markkinadataan. Puuttuvat tunnisteet jätetään pois; ei tekaistuja osakehintoja.
4. Aluksi suppea otos (esim. 30–100 likvidiä instrumenttia), jotta datalaatu, ETF-tyypit ja lähteen rajat voidaan tarkistaa. Koko valikoiman skannaus vasta riittävillä datan käyttöoikeuksilla, API-kapasiteetilla ja laskentabudjetilla.
5. Ei muutoksia tuotantopaperisalkun sääntöihin ennen erillistä ajallista validointia, tulevia paperituloksia ja käyttäjän hyväksyntää.

Tämän vaiheen uudet tiedostot ovat **turvallisia offline-sovittimia**, eivät valmiita tuotantoskannereita.


## Trading 212 INVEST Practice -tilin lukuoikeudellinen yhteystesti (18.10.2026)

Käyttäjän pyynnöstä luotu turvallinen ja VAIN MANUAALISESTI KÄYNNISTETTÄVÄ GitHub Actions -workflow:
[Check Trading 212 DEMO metadata (read-only)](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/trading212-metadata-check.yml).

- Lukee vain https://demo.trading212.com/api/v0/equity/metadata/instruments -päätettä (HTTP GET).
- Tulostaa onnistuneen ajon jälkeen pelkästään osakkeiden/ETF:ien kappalemäärät, yksilöllisten ISINien määrän, valuuttojen lukumäärät ja viimeisen 30 vrk:n alustalle lisättyjen instrumenttien määrän. Ei tulosta tai tallenna koko tilikohtaista instrumenttilistaa, saldoja, API-avaimia eikä toimeksiantoja. Trading 212:n addedOn ei ole pörssilistautumisen päivä.
- Workflowlla on vain contents: read -oikeus GitHub-repoon. Se ei tee Git-committeja eikä muuta paperisalkkua.
- Ei käytä API:n order-endpointeja eikä live.trading212.comia. Vaatii API-avaimen, jolla on **vain Metadata-lukuoikeus**.

**Tunnukset syötetään vain GitHubin salattuihin Repository Secrets -kenttiin (EI README:hen, GitHub-issueen, keskusteluun tai workflow-tiedostoon):**

1. Safari (iPhone) → [repository secrets](https://github.com/jaheinone-lang/swing-bot-iphone/settings/secrets/actions). GitHubin Settings → Secrets and variables → Actions, tarvittaessa Safari → Request Desktop Website.
2. New repository secret: `TRADING212_DEMO_KEY` = Trading 212:n näyttämä **API Key** (ei API Secret).
3. New repository secret: `TRADING212_DEMO_SECRET` = Trading 212:n näyttämä **API Secret**. Molemmat kentät ovat salaisuuksia eikä niitä saa lähettää ChatGPT:lle tai näyttää kuvakaappauksessa.
4. Actions → Check Trading 212 DEMO metadata (read-only) → Run workflow → main → Run workflow.
5. Avauduajon tulos on julkisesti luettavissa, joten tulosteessa on ainoastaan koostetietoja. Virhekoodi ei tulosta salaisia tunnuksia. Jos tietojen lukeminen ei onnistu, tarkistetaan käyttöoikeus, environment ja salaisuuksien oikeellisuus **tulostamatta itse arvoja**.

**Tila:** workflow valmiina, mutta yhteyttä ei ole vielä testattu käyttäjän oikeilla tunnuksilla. Trading 212 -avaimen IP-rajausta ei oteta käyttöön ennen kuin pysyvä/kiinteä palvelin-IP on käytössä. Nykyisen Github-hosted Actions -ympäristön lähde-IP voi muuttua. Jos tokenille myönnetään vahingossa kaupankäyntioikeudet, se tulee mitätöidä Trading 212:ssa ja luoda uudelleen minimioikeuksin.

## UUSI: Päivittäinen Trading 212 -katalogikatsaus ja TOP 20 -pisteytysrunko

**Varmennettu API-koe 18.10.2026:** [GitHub Actions, onnistunut](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39137310503).
Kokeessa saatiin 10 372 osaketta, 6 749 ETF:ää, 13 121 erillistä ISIN-tunnusta ja 923 Trading 212:een viimeisen 30 vuorokauden aikana lisättyä instrumenttia (ei 923 IPOa).

- [Päivittäinen tutkimusajo](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/trading212-daily-research.yml): ajastettu kerran päivässä UTC 05.37, sekä manuaalinen Run workflow. GitHub Actionsin ajastus voi viivästyä. Demo-API-avainpari on vain yksityisen lukutyötehtävän käytössä; julkinen julkaisutehtävä ei saa näitä salaisuuksia.
- [iPhonen seurantasivu](https://jaheinone-lang.github.io/swing-bot-iphone/): osakkeiden ja ETF:ien kokonaismäärät, markkinoiden valuutat, alustalle lisättyjen instrumenttien lukumäärä ja datalähteiden tila. Alkuarvot ovat 18.10.2026 onnistuneesta API-testistä; ensimmäisen automaattisen ajon jälkeen päivitys tapahtuu ajastetusti.
- `swingbot/universe_pipeline.py`: vain varmennetulla omalla tilillä saatavilla olevalla EUR-instrumentilla sekä luotettavalla, yritystapahtumaoikaistulla OHLCV-historialla laskettava TOP 20 -tutkimusranking. Käytössä ei vielä ole tarvittavaa erillistä hintasyötettä; sovitin **palauttaa tyhjän TOP 20:n**. Tietoja ei arvata.
- `tests/test_universe_pipeline.py`: testaa, ettei pelkkä metadatasyöte aiheuta rankingia, ettei rekisteröimättömiä tai väärän valuutan instrumentteja pääse mukaan ja ettei epäonnistunut API-haku korvaa edellistä raporttia.
- `docs/universe_research.json`: **ainoastaan luku- ja valuuttatilastot**, ei yhtään täydellistä instrumenttiriviä, API-tunnusta, saldoa, käyttäjän tietoa eikä toimeksiantoa. Jälkimmäisen työtehtävän julkaisu tarkistaa sallitut JSON-kentät ja estää julkaisun, jos niissä on yllättävää sisältöä.

**Seuraava tietoriippuvuus:** erillinen lähde vähintään 201 valmistuneelle OHLCV-päivälle per instrumentti, yhtiötapahtumien split-oikaisut, quote currency -varmistus sekä riittävä likviditeetti ja spread. Lisäksi SEC-/issuer-lähde aidolle pörssidebyytille (Trading 212:n `addedOn` ei ole IPO-päivä). Vasta näiden jälkeen 20 varmennetun ehdokkaan riskirajattu vertailu; aluksi paperisalkussa, ei live-ostoja.


## Maksuton US-osakedata (Massive US Stocks Basic)

18.10.2026 valmisteltu `swingbot/massive_free.py` ja [manuaalinen tutkimusajo](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/massive-free-research.yml).

**Palvelun viralliset tiedot:** [Massive Stocks -hinnoittelu](https://massive.com/pricing?product=stocks): Basic $0/kk, 2 vuotta historiallista US-osakedataa, enintään 5 API-kutsua minuutissa ja End of Day -data. Maksullinen Starter $29/kk (5 vuoden historia ja rajattomat kutsut palvelun ilmoituksen mukaan), Developer $79/kk (10 vuoden historia). Hinnoittelu voi muuttua. [Päiväkynttilöiden rajapinta](https://massive.com/docs/rest/stocks/aggregates/custom-bars).

**Käyttöönotto, kun käyttäjä päättää aloittaa:**
1. Rekisteröidy Massive-palveluun [massive.com](https://massive.com/), valitse maksuton **Stocks Basic** ja talleta API Key iPhonen Salasanat-sovellukseen. Älä lähetä avainta keskusteluun tai julkiseen GitHub-tiedostoon.
2. GitHub → tämän repon Settings → Secrets and variables → Actions → **New repository secret**. Anna nimeksi täsmälleen `MASSIVE_API_KEY`. Syötä API Key vain GitHubin salaiseen Value-kenttään.
3. Actions → [Free US stock EOD research test](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/massive-free-research.yml) → Run workflow. Ajo suorittaa ensin offline-turvatestit ja yrittää sitten hakea kahdeksan ennalta rajatun US-osakkeen valmiit USD-päiväkynttilät.
4. Ajo tulostaa vain kokonaismäärät `attempted/validated/failed`. Se EI tallenna eikä julkaise kaupallista per-instrumenttihintadataa tai rankingia, ei julkaise osaketunnuksia, eikä anna toimeksiantoja. Käyttöehdot on varmistettava ennen per-osakekohtaista julkaisua.

**Ajo on manuaalinen**, eikä Massive-avainta ole vielä kytketty tai sen toimivuutta varmennettu. Koodi on testattu keinotekoisilla tietueilla; ne **eivät** ole todellisia kursseja. Esimerkkiseurantalista: AAPL, MSFT, NVDA, AMZN, JPM, XOM, CAT, UNH. Haku on rajattu USD/US:ään, ei koko Trading 212 -valikoimaan.

**Rajaukset:** tiedot ovat vain osakespliteillä oikaistuja, eivät osingoilla, välittäjän symbolivastaavuutta (ISIN / kaupankäyntipaikka) ei ole varmennettu, reaaliaikaista spreadia ei ole mitattu eikä USD→EUR -konversiota ole todennettu. Riskiseulonnan esimerkkipisteet ovat tutkimushavaintoja; ne eivät vielä täytä 5 000 €:n EUR-paperisalkun hyväksyntäehtoja. Maksuton palvelu voi riittää noin 8–50 osakkeen tutkimiseen päivittäin, mutta koko US-markkinan ajantasainen päivittäinen läpikäynti vaatisi enemmän aikaa ja mahdollisesti maksullisen käyttöoikeuden. Paid provider does not imply improved strategy returns.


## Turvallinen US TOP 20 & A/B/C -kehitys (18.10.2026)

**Toteutettu koodiin, mutta EI liitetty oikeaan Massive-datasta laskettavaan kaupankäyntiin:**
- `swingbot/us_watchlist.py`: 50 ennaltavalittua yhdysvaltalaista yhtiötä (ei kulloinkin parasta top-50:tä). Pisteytys ja top-20 saa käyttää vain synteettistä fixture-dataa tai erikseen strategiakäyttöön lisensoitua oikeaa dataa.
- `swingbot/us_synthetic_lab.py`: kolme ennalta rekisteröityä USD-simulaatiomallia: A (20 päivän breakout, 50 päivän trendi, ATR x2), B (15 päivän breakout, 50 päivän trendi + 200 päivän ehto, ATR x2.5) ja C (10 päivän breakout, 30 päivän trendi + 200 päivän ehto, ATR x3). Riskiolettamukset: 5 000 **USD** kuvitteellinen erillissalkku, 1 % riski per positio, 20 % maksimipositiokoko, 5 yhtäaikaista positiota, 25 % lasku pysäyttää uudet avaukset, kummankin kauppasuunnan laskennalliset palkkiot 0,10 % ja liukuma 0,10 %. Kaikki signaalit edellisen sulkeutuneen päivän havainnoista, seuraavan päivän avaukseen simulointi. Samaan päivään osuva stop käsitellään varovaisesti. Kehitysjakso ensimmäiset 65 % 210 havainnon alkulämmittelyn jälkeisestä kalenterista ja loppuosa erillistä tarkistusjaksoa. Jokaisen jakson salkku aloitetaan erikseen; kaupankäyntitulosten ennustetta ei voida tehdä synteettisistä testeistä.
- `tests/test_us_synthetic_lab.py`: 50 symbolin tarkistus, lähde- ja valuuttarajaukset, väärän symbolin esto, tulevan päivän datan ulossulkeminen sekä strategiariskirajojen testit.
- [Swing Bot iPhone](https://jaheinone-lang.github.io/swing-bot-iphone/): uusi USA:n tutkimuslista -osio ja selkeä ilmoitus, ettei todellista TOP20:tä ole vielä laskettu.

**Massiven käyttöehtojen rajoitus löytyi 18.10.2026:** [Market Data Terms](https://massive.com/legal/market-data-terms-of-service) kohta 5(d) rajaa dataan perustuvia non-display-investointistrategioita ilman erillistä lisenssiä; myös datasta johdettujen tulosten julkaisu kolmannelle osapuolelle on rajoitettua kohdassa 5(c). Henkilökohtainen maksuton/premium-hinnoittelutaso **ei** yksin takaa näitä oikeuksia. Jo onnistuneen 8/8 rajapintatestin jälkeen [Massiven GitHub-testityönkulku](.github/workflows/massive-free-research.yml) on muutettu siten, että live-API-haku **ei käynnisty oletuksena**. Se suorittaa turvalliset offline-testit; erilliset oikeudet pitää todentaa ennen lisähakuja ja automatisoitua strategiakäyttöä.

**Dataoikeuksien varmistus on seuraava este.** Soveltuva vaihtoehto on datantuottajan kirjallinen non-display/derived-use -lupa tai eri lähde, jonka käyttöoikeus nimenomaisesti sallii oman automatisoidun strategiatutkimuksen. Lisäksi osakkeen Trading 212 -saatavuus, todellinen spread, USD/EUR-vaihto, yhtiötapahtumat, kaupankäyntikulut, rahansiirrot ja vero-oletukset on varmennettava ennen EUR-paperisalkkuun yhdistämistä. Oikeita kaupankäyntitoimeksiantoja ei muodosteta.
