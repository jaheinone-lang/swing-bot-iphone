# Päivänsisäinen 1 % nettovoiton kotiutus – tutkimusversio

Päiväys: 22.10.2026. Tämä on **kulukorjattu tavoitehinnan laskuri ja yksikkötestattu OHLC-poistumissääntö**, ei todellinen pörssitoimeksianto eikä luotettava 1–5 minuutin kurssihistoriaan perustuva tuottotesti.

## Tavoite

Onnistuneelle poistumiselle vähintään 1,0 % kaupan alkuperäisestä kustannuspohjasta (osto ja myyntikulut sekä oletettu kurssiliukuma sisältyvät), **ennen henkilökohtaista tuloveroa**.

Kaava:

```
target_raw_price = entry_raw_price * (1 + entry_slippage) *
  (1 + entry_fee) * (1 + target_net_profit) /
  ((1 - exit_slippage) * (1 - exit_fee))
```

Myyntitavoite pyöristetään ylöspäin seuraavaan sallittuun tick-kokoon, ettei pyöristyminen pudota laskennallista tavoitetta alle 1 %:n.

### Esimerkki, lähtöhinta 100 €

| Osto ja myynti erikseen | Myyntitavoite | Bruttokurssin nousu | Laskennallinen nettovoitto |
|---|---:|---:|---:|
| 0,25 % taker-palkkio ja 0,15 % liukuma per suunta | 101,82 € | +1,82 % | +1,009 % |
| Kaksinkertaiset kulut: 0,50 % + 0,30 % per suunta | 102,63 € | +2,63 % | +1,001 % |

Esimerkiksi 5 000 €:n **täyden position** nettovoitto onnistuneessa myynnissä olisi noin 50 € ennen veroja. Jos tästä positiosta myydään **puolet**, realisoitu nettovoitto on noin 25 €, ei 50 €. Myymättä jäänyt puolikas voi nousta tai laskea. Kaikissa vertailuissa laskennallinen tuotto perustuu toteutuneeksi oletettuun raakahintaan; tavoitehinnan pelkkä koskettaminen ei takaa toimeksiannon täyttymistä.

## Mitä toteutettu

- `swingbot/intraday_net_target.py`: hinnan laskenta, täyden kulukierroksen nettovoittoprosentti, osittaisen myynnin käteisvirta, konservatiivinen stop/take-profit-päätös valmistuneella OHLC-kynttilällä.
- `tests/test_intraday_net_target.py`: kulujen huomiointi, tick-pyöristys, osittaisen realisoinnin oikea tilikirjaus, samassa kynttilässä stop + tavoite = stop ensin.
- GitHub Actions näyttää laskelmat erillisenä osiona, eikä muuta nykyistä etenevää paperisalkkua.

## Oleelliset rajat

1. **Ei tuottotakuuta.** 1 % nettona on voittokaupan raja, ei yhden päivän keskimääräinen tuotto. Tappiollisia kauppoja voi olla paljon, eikä voittotavoite välttämättä toteudu.
2. Tämä koodi **ei vielä hanki 1–5 minuutin todellista historiallista hintadataa** tai testaa signaalin löytymistä, latenssia, likviditeettiä, tarjouseroja, markkinoiden nopeita liikkeitä tai osittaisia toimeksiantotäyttöjä. Ne ovat erillisiä toteutus- ja todentamisvaiheita ennen tuottoväitteitä.
3. Päivä- tai minuuttikynttilässä sekä stop- että tavoitehinta voi ylittyä, jolloin toteutumisjärjestys ei selviä pelkästä OHLC:stä; konservatiivisesti oletetaan stop ensin.
4. 1 %:n laskennallinen nettovoitto tarkoittaa nimenomaan kulujen jälkeistä, **ennen veroja**. Krypto-omaisuuden luovutusvoittoverotuksessa verokohtelu on yksilöllinen ja mahdolliset tuloverot vähentävät lopullista käyttäjälle jäävää voittoa.
5. Arvioidut pörssipalkkiot/liukuma eivät ole todellisia välittäjän sitovia tarjouksia. Riskiä voidaan rajoittaa, mutta sitä ei voi poistaa.


## 5 minuutin BTC-EUR -strategian ensimmäinen toteutunut historiatesti

Uudet tutkimusmoduulit:
- \`swingbot/bitvavo_intraday.py\`: julkisen Bitvavon BTC/ETH/SOL 1 minuutin ja 5 minuutin kynttilädatan lukeminen. Kesken oleva kynttilä poistetaan; puuttuvat 5 minuutin jaksot, virheelliset hinnat ja aikaleimat estävät testin.
- \`swingbot/intraday_research.py\`: yhden position BTC-EUR 5 minuutin läpimurtotutkimus, 20 valmiin kynttilän hintavertailu, osto vasta seuraavan kynttilän avauksessa, 20 % käytettävissä olevasta käteisestä yhteen ostoon, stop noin 1,5 % raakahintaa alempana. Ensimmäinen myynti on 50 % positiosta täsmälleen vähintään 1 %:n arvioidun kulujen jälkeisen tuoton kohdalla. Jäljelle jäävälle puolikkaalle kiristetään stop kulukorjattuun breakeven-hintaan.
- \`tests/test_intraday_research.py\`: valmis kynttilä, yhtenäiset 5 minuutin aikaleimat ja historiatestin turvallisuus.

[Ensimmäinen onnistunut GitHub Actions -ajo](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39808242191):
- 999 valmistunutta 5 minuutin kynttilää eli noin 3,5 päivää, data haettu Bitvavon julkisesta BTC-EUR-rajapinnasta testiajon yhteydessä.
- 5 000 € alkupääoma, arvioitu loppuarvo **4 968,39 €** (−31,61 €, −0,63 %).
- 3 ostoa, 1 puolen position 1 %:n nettovoittotavoitteen osuma, 2 stop-tapahtumaa.
- Testijakson suurin laskennallinen arvonlasku 0,67 %.
- Loppuarvo sisältää mahdollisen auki olevan position arvioidun likvidointiarvon, mutta **ei Suomen luovutusvoittoveron varausta**.
- Kauppamalli käyttää historiatietoa; se ei ole todellinen viiveetön toteutustesti eikä tilastollisesti merkittävä. Tästä ei voi päätellä odotettua päivävoittoa. Pörssikulut ja liukuma ovat oletuksia.

**Tärkeä:** strategia testattiin, ei otettu käyttöön oikeilla rahoilla eikä korvattu edellistä pidemmän aikavälin E-paperisalkkua. Uutta 1 % tavoitetta ei pidä kuvata 1 %:n päivätuottolupauksena.


## Lisätesti: 3 kryptoa × 3 peräkkäistä 5 minuutin testi-ikkunaa

[GitHub Actions 22.10.2026, onnistunut tutkimusajo](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39811729765)

Lisättiin \`swingbot/intraday_robustness.py\`: BTC-EUR, ETH-EUR ja SOL-EUR, jokaiselle kolme erillistä peräkkäistä ikkunaa, yhteensä yhdeksän lyhyttä koeikkunaa. Viiden minuutin historiaa on kunkin krypton osalta vain noin 1 000 kynttilää (noin 3,5 päivää). Kunkin ikkunan ostoille 80 vanhemman kynttilän valmistunut indikaattorihistoria, mutta **ei kauppoja lämmittelyjaksolla**. Simulointi aloitetaan kussakin ikkunassa erillisestä 5 000 eurosta; ikkunoiden tuottoja ei saa laskea yhdeksi sijoitetun pääoman kertymäksi. Kaksinkertaiset kulut testataan erikseen.

Vertailtavat kaksi mallia ovat nykyinen 20 kynttilän close-breakout ja tiukempi trendi + vahva vihreä kynttilä + 1,2 × 20 kynttilän volyymi + 14 kynttilän ATR (0,12–1,8 % hinnasta) + aiempien 20 kynttilän high-läpimurto. Molempien osto aikaisintaan signaalin **jälkeisen** viiden minuutin kynttilän avauksessa. Puolen position 1 % kulujen jälkeinen voittotavoite, stop etusijalla.

### Ensimmäiset BTC-EUR-koeikkunat, normaalit arvioidut kulut

| BTC-ikkuna | Vanha signaali | Tiukempi signaali |
|---|---:|---:|
| 1 | −35,39 € | −15,17 € |
| 2 | +14,45 € | +5,92 € |
| 3 | −34,48 € | −22,85 € |

Suodatettu malli pienensi kahta tappiollista jaksoa, mutta myös heikensi yhtä voitollista jaksoa. Testi on jälkikäteen suunniteltu ja **liian lyhyt** kannattavuuden vahvistamiseen. Kustannusarviot eivät korvaa toteutuneita spread-/täyttökustannuksia eikä henkilöveroja ole huomioitu. Älä yhdistä uusiin tilikirjanpitoihin tai ota live-kaupoiksi ennen aidosti riippumatonta pitempää testiä.
