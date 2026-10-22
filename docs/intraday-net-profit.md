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
