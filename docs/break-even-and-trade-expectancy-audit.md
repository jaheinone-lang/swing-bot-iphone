# Swing Bot: miksi 1 % nettotavoite ei vielä riitä?

Tutkimus 24.10.2026. Viiden vuoden varmennetut BTC-EUR ja ETH-EUR 5min-ajot: https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/40069155135

## Nykyinen strategia

- 5000 € yhteinen käteissalkku, korkeintaan 20 % varoista yhdessä positiossa; yksi osto Suomen kalenteripäivässä.
- 50 ostoa; 17 täyttä +1 % nettotavoitetta, 27 stop-myyntiä, 5 päivän loppusulkemista, 1 datakatkon pakkomyynti.
- 17/50 = 34 % ostoista saavutti tavoitteen. Historiallinen nettotulos -250,40 €, loppusaldo 4749,60 € (−5,008 %).
- Keskimääräinen onnistunut tavoitemyynti tuotti 5,24 € koko 5000 €:n lähtötilin näkökulmasta.
- 1 % tuotto enintään 1000 € positiolle = noin 10 € tilin tulosta ennen veroa ja muita pääomakuluja. Historiassa position koko oli usein pienempi riskiperusteisen mitoituksen vuoksi.

## Mekaaninen kannattavuusraja (ei strategian tuottoennuste)

Olkoon onnistuneen kaupan nettotuotto +1,00 % position hankintamenosta ja tappiollisen kaupan nettotappio L % position hankintamenosta. Kun jätetään iltasulut ja gapit huomiotta, voitollisten kauppojen vähimmäisosuus tasatulokseen on L/(L+1). Esimerkkejä:

| Keskimääräinen nettotappio L | Tarvittava voittoprosentti |
|---|---:|
| 1,00 % | 50,0 % |
| 1,50 % | 60,0 % |
| 2,00 % | 66,7 % |
| 2,30 % | 69,7 % |
| 2,50 % | 71,4 % |

**Tärkeä ero:** raaka 1,5 % stop-hintaväli ei ole nettotappio 1,5 %, sillä sisäänmenon ja stopin toteutuskulut sekä mahdollinen hintagap kasvattavat nettohäviötä. Jos molemmilla puolilla oletetaan 0,25 % palkkio + 0,15 % liukuma, 1,5 % raakahintastop vastaa likimäärin 2,29 % nettotappiota (yksinkertaistettu laskelma). Tasatulokseen tarvittaisiin silloin noin 69,6 % täysiä +1 % netto-voittoja **samankokoisilla positioilla** ja ilman muita poistumisia. Historiassa täydet TP:t olivat vain 34 % kaikista ostoista.

Huom: tämä on mekanistinen esimerkki, ei suora laskelma viiden vuoden toteutuneiden erikokoisten positioiden odotusarvosta. Todellinen break-even vaatii kaikkien 50 kaupan erilliset PnL:t ja niiden painotetun position koon, mukaan lukien päivä- ja gap-sulut.

## Historiallinen myyntien toteutumisherkkyys

| Oletus | Tuotto viidessä vuodessa |
|---|---:|
| Taker TP kosketus | −250,40 € |
| Taker 10bp hinnan ylitys | −253,56 € |
| Taker 30bp hinnan ylitys | −256,30 € |
| Maker TP 10bp hinnan ylitys | −244,94 € |
| Maker TP 30bp hinnan ylitys | −253,57 € |

**Päätelmä:** maker-palkkion etu on hyödyllinen mutta liian pieni korjaamaan 1 %:n tavoitteen ja 1,5 %:n raakahintastopin epäsuhtaa. Älä kasvata position kokoa tai kauppojen määrää ennen kuin nettotuotto-odotus on myönteinen myös riippumattomalla tulevalla paperidatalla.

## Seuraava oikea tutkimus

1. Raportoi jokaisen toteutuneen simuloidun kaupan entry, exit, nettotulos, position hankintameno, kesto, symboli, stop/tavoite/iltasulku ja vuosi. Laske toteutuneiden nettohäviöiden mediaani ja keskiarvo sekä EUR-painotettu odotusarvo; älä sekoita 1,5 % raaka-stoppia nettotappioon.
2. Mittaa erikseen signaalin jälkeen 15/30/60/120 minuutin suotuisin ja epäsuotuisin liike (MFE/MAE) *vain tulevan tutkimuksen diagnostisena mittarina*, ei signaalin lähtötietona.
3. Pidä osto- ja myyntimallit lukittuina tulevan datan paperiseurannassa. Mittaa order bookin spread ja mahdollisten maker-toimeksiantojen täyttymisaste, älä päättele toteutumia pelkästä kynttilän high-arvosta.
4. Jätä live-ostot, vipu ja automaattinen strategian vaihto pois käytöstä.

**Tutkimuksen rajoitus:** 5min OHLC-historian gap-segmentointi, arvioidut kulut ja toteutukset, ei henkilöveroja. Vuosia 2021–2026 on jo käytetty strategian kehittämiseen, joten niiden uusintatestit eivät ole riippumattomia.
