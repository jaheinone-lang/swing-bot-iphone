# BTC/ETH 1h kynttiläkuviot: ennustearvo vs kannattavuus

**Varmennettu GitHub Actions 12.11.2026:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/43282356700

## Tutkimuksen erottelu
- **Hinnan ennustearvo:** todellinen raakahinnan muutos 1, 4 ja 12 tunnissa seuraavan 5min kynttilän avauksesta; samaan kryptoon, vuoteen, kellonaikaan ja positiiviseen 24h trendiin sovitettu verrokki.
- **Kustannusherkkyys:** saman 1/4/12 tunnin hypotettinen kertakaupan kulujen jälkeinen nettotulos; normaalissa edestakaiset arvioidut palkkiot ja liukuma noin 0,8 %, stressissä noin 1,6 %. Nämä eivät ole toimivan salkun tuloksia.
- **Erillinen varsinainen salkkutesti:** max 1 osto/Suomen päivä, yhteinen 5000 € BTC/ETH-saldo, 1% nettoprofit TP, 1,5% raaka stop, klo 21.55 pakkomyynti. Ei henkilöveroja, ei oikeita toimeksiantoja.

Kaikki tutkimushistoria on aiemmin nähtyä: tulokset eivät ole prospektiivinen, riippumaton testi.

## Tuntikuvioiden raakahinnan kehitys

| Kuvio | Kynttilätapahtumia | 1h keskiarvo | 4h keskiarvo | 12h keskiarvo | 12h etu verrokkiin | 12h nettotuotto kuluilla |
|---|---:|---:|---:|---:|---:|---:|
| Bullish Harami | 172 | +0,0812 % | +0,1577 % (171) | +0,1397 % (171) | +0,2160 %-yks. | −0,6582 % |
| Vasara ja vahvistus | 108 | +0,0950 % | +0,1323 % | −0,2293 % | −0,1869 %-yks. | −1,0243 % |
| Yksinkertaistettu bullish Hikkake | 77 | −0,0724 % | −0,1270 % (76) | −0,1297 % (76) | −0,1131 %-yks. | −0,9255 % |

Haramin 12 tunnin raakakurssi nousi 56,73 % tapauksista, mutta samojen tasan 12h avaus/sulku -kauppojen nettotulos oli plussalla vain 36,84 % tapauksista. Haramin 1h, 4h ja 12h nettokeskiarvot olivat −0,7163 %, −0,6404 % ja −0,6582 %. Stressikuluilla 12h keskiarvo −1,4498 %.

## Varsinaisen salkkutestin tappiot

| Kuvio | 2021–2023 PnL € | 2024–2026 PnL € | 2024–2026 kaksinkertaiset kulut € |
|---|---:|---:|---:|
| Bullish Harami | −151,86 | −439,64 | −685,22 |
| Vasara ja vahvistus | −77,64 | −291,39 | −483,31 |
| Hikkake | −74,53 | −241,77 | −349,45 |

**Päätelmä:** Harami näyttää keskimäärin hieman parempaa raakahinnan kehitystä kuin sopivat verrokit, mutta marginaali jäi kulujen alle. Vasarassa 12h vaikutus kääntyi negatiiviseksi; Hikkake jäi negatiiviseksi kaikissa tutkituissa horisonteissa. Yksikään kuvio ei läpäissyt kannattavuutta. Ei live-käyttöä.

**Rajoitukset:** verrokit eivät ole kausaalisia; päällekkäiset tuntihorisontit; datakatkosegmentointi; vain arvioidut toimeksiantototeutumat ja kulut; jo aiemmin tutkittu data; verot pois. Hypoteettisen tasan 12h poistumisen nettolukua ei saa väittää koko salkun tuotoksi.
