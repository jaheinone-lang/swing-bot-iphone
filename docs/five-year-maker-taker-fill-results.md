# Viiden vuoden BTC + ETH -myyntitoimeksiantojen täyttöherkkyys

Päivitetty 24.10.2026. **Tarkistettu ja onnistunut tutkimusajo:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/40069155135

## Tulokset

Yksi yhteinen 5 000 €:n spot-käteissalkku; BTC-EUR ja ETH-EUR, yksi osto Suomen kalenteripäivää kohti, lukittu morning_strict-ostosääntö, 50 ostoa viidessä vuodessa. Koko position 1 %:n nettotavoite ennen veroja, alkuperäinen stop-loss ja klo 21.55 sulku ennallaan. Historialliset 5 min OHLCV-kynttilät Bitvavolta, ei order book -tietoa.

| Täyttöoletus | Täydet TP-myynnit | Loppu EUR | PnL EUR | PnL EUR, 2× kulut |
|---|---:|---:|---:|---:|
| Alkuperäinen taker: tavoitehinnan kosketus | 17 | 4 749,60 | −250,40 | −347,41 |
| Taker: 0,10 % ylitys | 16 | 4 746,44 | −253,56 | −349,85 |
| Taker: 0,30 % ylitys | 15 | 4 743,70 | −256,30 | −349,34 |
| Maker-myynti: 0,10 % ylitys | 18 | 4 755,06 | −244,94 | −304,33 |
| Maker-myynti: 0,30 % ylitys | 16 | 4 746,43 | −253,57 | −327,52 |

Maker-skenaariossa ostot ja stopit ovat taker-oletuksella; onnistunut TP oletetaan maker-kuluksi 0,15 % ja ilman myynnin slippagea. Taker-perusskenaariossa palkkio 0,25 % ja slippage 0,15 % molemmin puolin. Maker-TP:n matalampi tavoitehinta selittää, miksi 0,10 %:n ylityksellä TP-lukumäärä voi olla suurempi kuin alkuperäisellä taker-kosketuksella.

**Rajoitukset:** 5 min kynttilän high:n 10 tai 30 korkopisteen ylitys ei takaa, että limiittimyynti täyttyisi. Maker-toimeksianto voi jäädä jonoon tai toteutua osittain; stop voi liukua. Datakatkot, viiden minuutin sisäinen järjestys, likviditeetti, order book ja Suomen henkilöverot eivät ole täydellisesti mukana. Tuloksia ei saa tulkita toteutuneiksi kaupoiksi eikä tulevan kannattavuuden todisteeksi.

**Johtopäätös:** kaikkien viiden mallin tulos on tappiollinen koko viiden vuoden historialla. Maker-mallin 0,10 % ylitys oli vähiten tappiollinen mutta vain 5,46 € parempi kuin vanha vertailumalli. **Ei käyttöönottoa, ei riskin kasvattamista, ei oikeita toimeksiantoja.** Seuraava tutkimus: todellisen toimeksiantokirjan ja spreadin paperiseuranta sekä kulujen jälkeen voitollisen ostoedun arviointi uudella, ennestään näkemättömällä datalla.
