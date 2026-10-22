# Kryptostrategian tutkimus 22.10.2026

Tämä on **vain historiatutkimus**. Ei kauppojen välitystä, API-avaimia, oikean rahan kauppoja, eikä muutosta nykyiseen jatkuvaan paperisalkkuun.

## Toistaminen

```bash
python -m unittest discover -s tests -v
python -m swingbot.crypto_alpha_research
```

Myös [GitHub Actionsin Crypto alpha research -ajo](../actions/workflows/crypto-alpha-research.yml) suorittaa tutkimuksen julkisilla, valmistuneilla Bitvavon BTC-, ETH- ja SOL-eurokynttilöillä. Työnkulku kirjoittaa raportin GitHub Actions -yhteenvedoksi, ei sijoitustoimeksiannoiksi eikä pysyvään salkkuun.

## Jäädytetyt tutkimusvaihtoehdot

- A: nykyinen 20 päivän läpimurto, 50 päivän trendi, 20 % enimmäispositio, 1 % laskennallinen riski per kauppa.
- D: 10 päivän läpimurto, 30 päivän trendi, 55 % enimmäispositio, 2 % riski, 15 päivän aikapoistuminen.
- E: 15 päivän läpimurto, 50 ja 200 päivän trendisuodatus, 60 % enimmäispositio, 2 % riski, 30 päivän aikapoistuminen.

D ja E ovat tarkoituksellisesti aiempaa aggressiivisempia. Jäljelle jäävät EUR-määräiset käteisvarat ovat mukana mallissa. Pitkät positiot ilman vivutusta ja ilman shorttausta. Kaupankäynti simuloidaan sulkeutuneen päivän signaalin jälkeisen päivän avaukseen, ja stopit voivat toteutua huonompaan hintaan avausgapissa.

Historiallisessa testissä käytettyjen kustannusten perusoletus on 25 korkopisteen toimeksiantopalkkio + 15 korkopisteen slippage per puoli; kustannusstressissä kumpikin kaksinkertaistetaan. Tuotot sisältävät yksinkertaistetun Suomen henkilöverotukseen perustuvan varauksen **realisoituneille** voitoille, eivät lopullista henkilökohtaista verotusta tai avoimien positioiden mahdollisia veroja.

### Ensimmäinen GitHub Actions -havainto, 22.10.2026

Bitvavon valmistuneet päiväkynttilät 2.11.2024–21.10.2026, 719 kalenteripäivää, aloitus 5 000 €:

| Malli | Kehitysjakson tuotto | Myöhempi jakso | Myöhemmän jakson suurin arvonlasku | Koko ajan arvo verovarauksella | 2x kulut: arvo verovarauksella |
|---|---:|---:|---:|---:|---:|
| A | +1,73 % | +4,91 % | 4,36 % | 5 336,24 € | 5 180,30 € |
| D | −14,64 % | +25,94 % | 9,82 % | 5 375,04 € | 5 095,71 € |
| E | +2,01 % | +12,57 % | 9,14 % | 5 741,43 € | 5 657,81 € |

Malli E valikoitui **vain kehitysjakson** pisteytyksellä (tuotto prosenttiyksikköinä −1,5 × suurin arvonlasku). Myöhempi jakso raportoitiin sen jälkeen. Tämä ei ole aidosti etukäteen riippumattomasti vahvistettu testi, koska strategioita on hahmoteltu jo historiallista tietoa tuntien.

**Tulokset eivät ole ennusteita tai sijoituspäätösperuste.** Vertailu koskee vain kolmea kryptoa ja noin kahta vuotta; eri markkinasykleissä, kuluissa ja toteutuksissa tulos voi olla negatiivinen. Historiallisen OHLC-aineiston perusteella ei voida taata stop-hintaa tai 25 %:n enimmäistappiota. Ennen oikeaa sijoitustoimintaa tarvitaan vähintään lisää riippumatonta historiaa, pidempi muuttamattomin säännöin tehty forward-paperikauppa sekä todelliset välittäjäkulut ja toimeksiantojen toteutustestit.
