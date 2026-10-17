# Swing Bot iPhone — kehitysversio

Tämä projekti on **vain testikäyttöön tarkoitettu swing-kaupankäynnin signaalimoottori**. Se ei yhdistä pörssiin, välittäjään tai kryptopalveluun eikä tee oikeita kauppoja.

## Strategia (prototyyppi)

- Päätöskurssi ylittää edellisten 20 havaintopäivän korkeimman päätöskurssin.
- Päätöskurssi ylittää edellisten 50 havaintopäivän päätöskurssien keskiarvon.
- ATR (14 havaintopäivää) määrittää simuloidun stop-etäisyyden (2 × ATR).
- Positiokohtaisen riskin laskennallinen yläraja on 1 % käytetystä salkun arvosta, ja position nimelliskoko enintään 20 %.
- Jos salkun simuloitu arvonlasku huipustaan on vähintään 25 %, uudet ostosignaalit pysäytetään. **Tämä ei takaa todellisen enimmäistappion rajaa.** Kurssihypyt, kaupankäyntikulut ja toteutushäiriöt voivat kasvattaa tappioita.
- Malli ei vielä huomioi kaupankäyntikuluja, veroja, liukumaa, avoimia positioita eikä historiallista kokonaisstrategian tuottoa.

## Näin näet tuloksen iPhonella

Avaa [GitHub Actions](https://github.com/jaheinone-lang/swing-bot-iphone/actions) → **Python safety tests** → uusin onnistunut ajo. Sen **Example signal (SIMULATION ONLY)** -kohdassa näkyy esimerkkidatan perusteella laskettu signaali. Tämä ei ole todellinen osto-/myyntisuositus.

## Kehittäjän kokeilu

Tarvitaan Python 3.11+ eikä ulkoisia kirjastoja.

```bash
python -m unittest discover -s tests -v
python -m swingbot.cli data/demo_prices.csv --equity 5000 --peak-equity 5000
```

CSV-sarakkeet: `date,high,low,close`. Esimerkkidata on keksittyä, eikä siinä ole aitoa kaupankäyntikalenteria.

## Seuraavat vaiheet

1. Valitaan treidattava markkina, sallittu välittäjä ja instrumentit.
2. Lisätään hinnanlähde, oikea backtest sekä kulut, slippage ja rahankäytön rajoitukset.
3. Rakennetaan paperikaupankäynti ja iPhonen selainkäyttöliittymä.
4. Oikeat toimeksiannot vasta erillisen turvallisuustarkistuksen ja nimenomaisen hyväksynnän jälkeen.

**Älä koskaan tallenna API-avaimia GitHubiin.** Projekti on tällä hetkellä julkinen.
