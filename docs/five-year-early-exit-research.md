# BTC/ETH viiden vuoden kokeellinen varhaisen myynnin tutkimus

Tarkastettu 23.10.2026. Testiajo: https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39905670254

## Tavoite

Tutkia viiden vuoden (23.10.2021 – 22.10.2026) oikeiden BTC-EUR ja ETH-EUR 5 minuutin hintatietojen perusteella, voisiko 1,5 %:n suojastoppiin asti odottamisen sijasta *sulkea menettävän ostomomentumin* aiemmin ja vähentää nettotappioita. Salkku: yksi 5 000 € käteistili, osto enintään kerran päivässä yhteensä, tiukka aamun ostosignaali, täysi +1 % nettotavoite toteutuneeksi mallinnettuna, stop tai klo 21.55 lopetus. Riski kauppaa kohden nimellisesti enintään 0,25 % tilistä, positio enintään 20 %.

## Kolme vertailtua exit-sääntöä

1. **Perusmalli:** +1 % nettovoittotavoite myy koko position, muutoin 1,5 % raakahinnan stop tai kello 21.55 sulku Suomen aikaa.
2. **Kolme laskevaa sulkeutumista:** odotetaan vähintään 20 minuuttia ostosta, edellisten neljän valmiin kynttilän sulkeutumishinnat laskevat peräkkäin, hinta on sisäänmenohintaa ja 20 kynttilän keskihintaa alempana; myy seuraavan kynttilän avauksessa.
3. **90 minuutin heikkoussulku:** vähintään 90 minuuttia ostosta, viimeisen valmistuneen kynttilän hinta alle sisäänmenohinnan, 20 kynttilän liukuvan keskihinnan sekä kolmea kynttilää aiemman tason; myy seuraavan kynttilän avauksessa.

**Varhainen poistuminen ei muuta 1 %:n nettovoittotavoitetta eikä 1,5 %:n stopia**, mutta se voi toteutua aikaisemmin. Jos stop-hinta ylittyy jo avatessa, stop käsitellään ennen varhaista poistumista; täysi voitontavoite avatessa käsitellään myös ensin. Varhaisen poistumisen ehtona käytetään *vain edellisiin valmistuneisiin kynttilöihin* perustuvaa havaintoa, jolloin tulevaa hintaa ei vuoda päätökseen.

## 5 vuoden tulokset, Bitvavon BTC-EUR / ETH-EUR

525 888 odotettua 5 min kynttilää per pari. BTC havaittua 523 661, ETH 521 788. Yhteensä 505 799 kelpuutettua yhteistä kynttilää 691 yhtenäisessä jaksossa; **ei hinnan täyttöä aukkoihin**.

| Exit | 5v ostoja | Täydet +1 % nettopoistumiset | Stopit | Varhaiset poistumiset | 5v tulos € | 2× kulujen tulos € |
|---|---:|---:|---:|---:|---:|---:|
| Perusmalli | 50 | 17 | 27 | 0 | **−250,40** | **−347,41** |
| 3 laskevaa 5 min sulkua | 50 | 7 | 1 | 42 | **−244,96** | **−335,47** |
| 90 min heikkous | 50 | 8 | 2 | 40 | **−234,26** | **−336,91** |

Normaalikuluoletus: 0,25 % kaupankäyntipalkkio + 0,15 % liukuma per puoli. Stressikulut: 0,50 % + 0,30 % per puoli. Kokonaisviiden vuoden euromääräinen parannus 90 min säännöllä **+16,14 €** perusmalliin nähden (salkun alkuarvosta +0,32 prosenttiyksikköä). Kaikki mallit pysyvät tappiollisina ennen henkilöveroja.

### Miksi en ota varhaista poistumista automaattisesti käyttöön

- 90 min vaihtoehdossa 40/50 kauppaa poistui varhain: myös aiemman perusmallin osumista moni olisi jäänyt tulematta, täysiä 1 % TP-tapahtumia 17 → 8.
- Parannus koko viiden vuoden aikana vain 16,14 €; se on pienempi kuin toteutumattomien toimeksiantojen spread/slippage-epävarmuudet voivat hyvinkin olla.
- Vuosina 2021–2025 perusmallin yhteenlaskettu arvioitu tulos oli noin **−274,54 €**, 3 laskevaa **−213,39 €** ja 90min **−222,78 €**. Vuonna 2026 perusmalli oli **+24,13 €** mutta 3 laskevaa **−31,58 €** ja 90min **−11,49 €**. Tämä osoittaa vaihtoehtojen riippuvan markkinaympäristöstä; *kumpikaan ei voittanut perusmallia vuonna 2026*.
- Myös kaksinkertaisilla kuluilla kaikki vaihtoehdot negatiivisia. Oikeita limit-täyttöjä, spreadia ja Suomen veroja ei ole validoitu.
- Sama viiden vuoden historia on osa jo analysoitua datasettiä, joten päättely ei ole riippumaton prospektiivinen testi. Sääntöjen käyttö vaatii vielä erillisen lukitun, eteenpäin kulkevan paperitestin.

### Koodi ja auditointijälki

- `swingbot/daytrade_exit_guards.py`: kaksi uutta syy–seurausjärjestyksen säilyttävää poistumistapaa
- `swingbot/daytrade_one_per_day.py`: valinnainen guard; perusmalli säilyy muuttumattomana guard=None
- `swingbot/five_year_daytrade.py`: mallin simulointi valinnaisella poistumistavalla
- `swingbot/five_year_early_exit.py`: kolmen vaihtoehdon oikea 5 vuoden vertailu
- `tests/test_daytrade_exit_guards.py`: tarkastaa tulevan kynttilän ohittamisen, gap-stopin prioriteetin ja 90 minuutin rajan
- `.github/workflows/crypto-early-exits.yml`: onnistunut GitHub Actions -ajo ja latauskelpoinen JSON-raportti

**Ei oikeita toimeksiantoja, ei olemassa olevan E-paperisalkun muutoksia, ei mallin hyväksyntää oikealla rahalla ajettavaksi.**
