# Kokonaissalkun positiivisten sääntöjen haku: 5 vuoden BTC/ETH-kokeilu

**Varmennettu onnistunut GitHub Actions -ajo:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/40209559115

**Koko tutkimusikkuna:** Bitvavon BTC-EUR/ETH-EUR-aidot 5 min kynttilät ajalta 23.10.2021–22.10.2026. Käytettiin samaa read-only 5 vuoden historiatekniikkaa: katkojen segmentointi, 160 kynttilän lämmittely, yksi yhteinen EUR 5000 spot-salkku per vaihtoehto, enintään yksi osto Suomen kalenteripäivässä, 100 % position poistuminen nettoprofit-tavoitteeseen, stop tai klo 21.55 Suomen aikaa, ei vipua. Normalisoitu oletuskulupohja: osto/myynti 25 bps palkkio + 15 bps slippage. 2x kuluilla molemmat tuplana. Nettotavoite ennen veroja.

**Menetelmä:** kuusi kokonaissalkun hypoteesia päätettiin ennen tulosten lukemista. 2021–2023 vanhempi harjoitusjakso ja myöhempi 2024–2026 vertailujakso ovat **kumpikin itsenäisiä aloituksia 5000 eurosta**, eivät yhden tilin vuodenvaihteen jatko. Kelpuutus harjoitusjaksolla: vähintään 15 kauppaa + positiivinen kokonais-PnL sekä normaalikuluilla että 2× kulustressissä. Myöhempi jakso edellyttäisi lisäksi 15 kauppaa sekä positiivista tulosta molemmilla kuluilla. Vanhaa tutkimushistoriaa on jo katsottu, joten nämä eivät ole aidosti tulevan markkinan riippumattomia testejä.

## Varmennetut tulokset

| Hypoteesi | Vanhempi jakso: ostot | Vanhempi PnL € | Vanhempi 2x kulut € | Myöhempi jakso: ostot | Myöhempi PnL € | Myöhempi 2x kulut € |
|---|---:|---:|---:|---:|---:|---:|
| BTC + ETH yhdistelmä | 9 | −76,08 | −100,85 | 41 | −177,03 | −251,65 |
| ETH-only | 3 | −19,53 | −37,41 | 28 | −111,13 | −157,33 |
| BTC-only | 6 | −56,78 | −63,92 | 17 | −84,30 | −122,51 |
| Stop 0,8 % | 9 | −71,39 | −101,36 | 41 | −249,70 | −319,58 |
| Stop 2,5 % | 9 | −43,39 | −71,68 | 41 | −111,54 | −172,70 |
| Täysi nettoprofit 2 % | 9 | −97,15 | −100,85 | 41 | −161,35 | −255,71 |

**Yksikään malli ei läpäissyt harjoitusjakson eikä molempien jaksojen hyväksyntäehtoja.** Yhteenkään kauppamalliin ei tehty automaattista vaihtoa.

Leveämpi 2,5 % raakahintastop oli **vähiten tappiollinen** kokonaissalkun yhdistelmävaihtoehdoista kummallakin jaksolla, mutta edelleen selvästi miinuksella ja vuonna 2021–23 vain 9 oston aineistolla. Stoppiriskin euromääräinen yläraja pysyy ennen kulu- ja slippage-hypoteeseja nimellisesti 0,25 %:ssa pääomasta riskiperusteisen position mitoituksen vuoksi; slippage/gapit voivat ylittää sen. Väite, että leveämpi stop takaisi tulevan kannattavuuden, olisi perusteeton.

## Millaisia sääntöjä tämän jälkeen kannattaa tutkia?

- **Todellinen kaupankäyntietu:** onko vahvistettu nousu enemmän kuin satunnaisesti poimittujen saman hetken BTC/ETH-kauppojen tuotto, kulujen jälkeen? Tarvitaan samalla aikajaksolla verrokkiryhmä, mielellään walk-forward.
- **Kulurakenne:** toteutuuko +1 % nettotavoite oikeasti maker-/taker-toimeksiannolla vai jääkö limiittimyynti täyttymättä? 5 min OHLC `high` ei riitä.
- **Uusi, prospektiivinen lukittu forward-only paperiseuranta** eikä jälkikäteen raja-arvojen optimointi vuodesta 2021 alkaen. Kauppojen vähäinen määrä aiheuttaa suuret otosepävarmuudet.
- **Mittaa myös käyttämättä jäänyt käteinen, toteutuneet stop-gapit, position koko ja verot** ennen pääoman kasvattamista.

Ei uusia oikeita toimeksiantoja, ei muutosta olemassa olevaan E-paperisalkkuun. PR #1 säilytetään luonnoksena.
