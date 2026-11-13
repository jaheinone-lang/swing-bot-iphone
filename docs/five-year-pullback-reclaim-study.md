# BTC + ETH: viiden vuoden takaisinvetoon perustuvien ostojen tutkimus

**Päivä:** 23.10.2026. **Viiden vuoden aineisto:** 23.10.2021–22.10.2026 UTC Bitvavo BTC-EUR ja ETH-EUR viiden minuutin todelliset kynttilät.

**Onnistunut GitHub Actions -ajo:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/40012946763

## Testisuunnitelma

Tarkoitus on testata, välttäisikö botti hintapiikin huipulta ostamisen odottamalla hallittua takaisinvetäytymistä ja vahvistettua nousun jatkumista.

Säilytettiin ennallaan:
- Yksi yhteinen EUR 5 000 käteissalkku, vain BTC ja ETH.
- Enintään yksi osto päivässä Suomen aikavyöhykkeellä, klo 09.00–13.59.
- Valmis viiden minuutin kynttilä laukaisee oston **seuraavan kynttilän avauksessa**; ei tulevaisuusdataa.
- Yhden position maksimi 20 % salkun markkina-arvosta, suunniteltu stop-riski 0,25 % pääomasta, ei velkavipua.
- Täysi 100 % kotiutus kun laskennallinen kaupankäyntikulujen ja liukuman jälkeinen **+1 % nettotavoite** täyttyy (ennen pääomatuloveroa), muuten stop tai päivän lopun sulku klo 21.55.
- Kulumalli osto ja myynti kummallakin 0,25 % palkkio ja 0,15 % arvioitu liukuma; stressissä molemmat kahdinkertaisena.

Uudet **ennen tämän ajon tulosten näkemistä koodatut** ostohypoteesit:
1. **breakout_pullback_reclaim:** sulkeutunut läpimurto 3–12 kynttilää aiemmin, sen jälkeinen laskeva kahden kynttilän korjaus, 20 kynttilän keskiarvon läheinen retesti ja vahva nouseva palautumiskynttilä edelleen 20>50>100 SMA -nousutrendissä.
2. **trend_pullback_reclaim:** 20>50>100 SMA -nousutrendi, kaksi laskevaa sulkuhintaa ja sitä seuraava vahva nouseva palautuminen 20 SMA:n tuntumasta ilman aiemman läpimurron vaatimusta.

**Säännöt ovat retrospektiivisiä.** Sama viiden vuoden aineisto on jo aiemmin tutkittu; edes jakovuosien 2021–2023 ja 2024–2026 vertaaminen ei tee tästä täysin riippumatonta eteenpäin kulkevaa testiä.

## Varmennetut tulokset, yksi yhteinen 5 000 € salkku per skenaario

| Ostomalli | Ostot | 100 % position +1 % nettotavoitteen myynnit | Stopit | Iltasulut | Loppusaldo | Nettotulos ennen veroja | Nettotulos 2× kuluilla |
|---|---:|---:|---:|---:|---:|---:|---:|
| Aiempi tiukka aamustrategia | 50 | 17 | 27 | 5 | **4 749,60 €** | **−250,40 €** | **−347,41 €** |
| Breakout → korjaus → uusi nousu | 75 | 19 | 42 | 14 | 4 525,99 € | −474,01 € | −584,82 € |
| Nousutrendi → korjaus → palautuminen | 151 | 43 | 82 | 26 | 4 156,32 € | −843,68 € | −1 025,15 € |

Vanhan strategian yhtenäisen jakson katkosulkuja 1, uusissa malleissa 0. Tulos ei ole täysin katkeamaton koko viiden vuoden replay, koska puuttuvat kynttilät on eroteltu eikä täytetty.

### Vuosijaksot — nettotulos normaalikuluilla

| Ostomalli | 2021–2023 (osavuosi 2021) | 2024–2026 (osavuosi 2026) |
|---|---:|---:|
| Aiempi tiukka aamu | −76,09 € | −174,32 € |
| Breakout + takaisinveto | −154,67 € | −319,31 € |
| Nousutrendi + takaisinveto | −278,85 € | −564,85 € |

## Tulkinta ja päätös

- Nykyinen ostomalli teki 50 kauppaa ja 17 voitollista täydellistä nettotavoitepoistumista (~34 % ostojen määrästä).
- Läpimurron takaisinveto tuotti 75 kauppaa ja 19 tavoiteosumaa (~25 %).
- Pelkkä trendin takaisinveto teki 151 kauppaa ja 43 tavoiteosumaa (~28 %).
- Kaikki uudet mallit kasvattivat stop-tapahtumien määrää huomattavasti, ja molempien historiallinen tulos heikkeni myös 2× kustannusstressissä.
- Yksikään uusi sääntö ei osoittanut kannattavaa tuotto-odotusta eikä niitä oteta käyttöön edes aiemmassa paperitilissä.
- Tutkimuksen seuraava suunnittelu kannattaa kohdistaa kaupankäyntikulujen / voittotavoitteen realistisuuteen, kaupankäyntiä edeltävän signaalin informaatioarvoon ja aidosti uusien hintojen paperitestaukseen; ei voittajamallin optimointiin jälkikäteen.

**Rajoitukset:** OHLC:n ylin hintataso ei todista limiittitoimeksiannon täyttöä, hinnan liukumaa tai stopin toteutumista. Puuttuvien havaintojen vuoksi aineisto on jaettu jaksoihin, joissa mahdolliset avoimet positiot realisoidaan laskennallisesti; ei veroja, oikeaa likviditeettiä tai order bookin hintatasoa. Viiden vuoden tulos on mallinnus, ei tulevan tuoton lupaus.

**Koodi:** `swingbot/pullback_reclaim_5year.py`, `swingbot/five_year_pullback_research.py`, `tests/test_five_year_pullback_research.py`. Työnkulku `.github/workflows/crypto-five-year.yml`. Ei pörssitunnuksia tai live-toimeksiantoja. PR pysyy luonnoksena.
