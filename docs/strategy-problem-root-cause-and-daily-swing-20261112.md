# BTC/ETH: Miksi lyhyet kynttiläkaupat häviävät ja mitä 1d swing-testit muuttivat

**Varmennetut GitHub-ajot:**
- 5 min / 4 h trendin ja 24/72h swing: https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/43284396825
- Todelliset 1d Bitvavon BTC-EUR ja ETH-EUR päivähistorian tulokset ja vuosijako: https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/43286400438

**Historiallinen rajaus** 2021-10-23 — 2026-10-22. 1826 peräkkäistä 1d-havaintoa kummastakin instrumentista Bitvavolta, ei interpolointia. Vuodet 2021–23 ja 2024–26 aloitetaan kumpikin omasta 5000 €:n salkusta. Päivähistorian 200 päivän indikaattorilämmittely rajaa vanhemman jakson ensimmäisiä ostomahdollisuuksia. 5 min -historiassa oli 691 yhtenäistä jaksoa ja 505799 yhteistä simulaatiokelpoista 5 min kynttilää; 4h-swing-analyysi vaatii tästä vielä pitkän aukottoman lämmittelyn.

## Ongelman ydin

- Alkuperäinen 1 %:n nettotavoite ja 1,5 %:n raakahintastop: 50 kauppaa, 17 tavoiteosumaa, 27 stopia. EUR 5000 → 4749,60 viidessä vuodessa, ennen veroja. Keskimääräinen voitollinen kauppa +4,97 €, tappiollinen −10,62 €.
- Kynttiläkuvioiden 1/4/12 tunnin raakakurssimuutokset ovat useimmiten vain noin 0,1–0,2 %; ostamisen ja myymisen oletetut palkkiot ja liukuma yhteensä noin 0,8 %. Tällainen etu ei riitä.
- Myös 4h signaaleista tehdyt 24/72 h pidot jäivät tappiolle molemmilla ajanjaksoilla, ja kulustressi heikensi tuottoja.

## Todellisen 1d datan pitkä trendi

Kaikissa kolmessa spot-swing-mallissa vain yksi yhteinen EUR5000 tili, max 20 % avoimessa positiossa, nominal stop-risk 0,25 % salkusta, 4 % raakahintastop, 3 päivän jäähtymisaika myynnin jälkeen, kauppa vasta valmistuneen päiväkynttilän jälkeen seuraavan päivän OPEN-hintaan, 60 päivän maksimipitoaika. Ei vipua eikä oikeita kauppoja. Palkkiot Bitvavon tyypillisen alimman taker-tason (0,25 %/puoli) ja arvioidun liukuman (0,15 %/puoli) mukaiset; lisäksi 2× kulustressi.

| Hypoteesi | 2021–2023 PnL € | 2024–2026 PnL € | 2024–2026 2× kulut € | 2024–2026 kauppoja |
|---|---:|---:|---:|---:|
| 20 päivän ylärajan läpimurto | −5,98 | +70,69 | +31,55 | 16 |
| **55 päivän ylärajan läpimurto** | **−59,12** | **+129,21** | **+88,53** | **12** |
| Nousutrendin 20 päivän keskiarvon takaisinvaltaus | −43,92 | +33,73 | +5,56 | 13 |
| EUR-käteinen | 0 | 0 | 0 | 0 |
| 20 % BTC/ETH ostettu ja pidetty (80 % käteistä) | +131,99 | +444,40 | ei laskettu | 2 ostoa |

**Erityisesti 55 päivän läpimurto, 2024–2026:** 2024 +114,58 € (5 suljettua kauppaa), 2025 +11,89 € (4), 2026 +2,75 € (3) — ennen veroja. Vuoden 2024 tulos on noin 89 % koko myöhemmän jakson +129,21 €:sta. Vuoden 2026 tulos on niin pieni ja kaupankäyntien lukumäärä niin vähäinen, ettei heikon markkinan kestävyydestä voi päätellä myönteistä etua. Vuosiluvut luokiteltu kaupan *poistumisvuoden* mukaan, eivät mark-to-market -vuosituottoja.

**Tulkinta:** lyhyen aikavälin päästö ei ollut ratkaisu. Päiväkynttilöiden 55 päivän breakout oli uudemman historian perusteella ensimmäinen kiinnostava, normaalikuluilla ja kaksinkertaisilla kuluilla nettovoitollinen aktiivinen malli. Mutta vanhempi jakso oli edelleen tappiollinen; lisäksi sekä 2021–23 että 2024–26 perus-BTC/ETH buy-and-hold 20% painolla tuotti enemmän ilman jatkuvaa treidausta. Pitkien positioiden yön yli -riskit, datahan jo tutkittu, 4% stopin 5min sisäinen täyttö ja pääomatulovero vielä arvioita.

## Päätös (ei sijoituslupausta)

- *Ei yhtään strategiaa hyväksytä live-kauppaan.* Tällä hetkellä todistettua positiivista kaupankäyntietua ei löydy eri markkinakausilta ja riittävän itsenäisestä datasta.
- Jos käyttäjän tavoitteena on vähentää tarpeettomia tappioita, konkreettinen toteutusratkaisu on **kaupankäyntikielto**, kunnes lukittu 55 päivän 1d breakout tai muu uusi malli osoittaa prospektiivisesti positiivisen kulut jälkeisen odotusarvon hyväksyttävällä tappioriskillä.
- Paperisalkussa voidaan seurata lukittua 55 päivän breakout-mallia rinnakkain 20% buy-and-hold + 80% käteinen -vertailuun; mitataan myös maksimi arvonlasku, todelliset tarjouskirjan spreadit, maker/taker-fill ja verot.
- Jos passiivinen verrokkisalkku voittaa myös riskisuhteisesti, aktiivinen botti on tarpeeton. Tämä on sallittu ja keskeinen tulos.
