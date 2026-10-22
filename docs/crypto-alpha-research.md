# Kryptobotti: riippumaton kehityslaboratorio ja uusi forward-paperisalkku

Päivitetty 22.10.2026. Kaikki on tutkimusta. Ei oikeita rahasiirtoja, ei toimeksiantoja, ei API-kaupankäyntiavaimia. Olemassa oleva `paper/state.json` on jätetty ennalleen.

## Testatut jäädytetyt mallit

- A: 20 päivän läpimurto, 50 päivän trendisuodatin, korkeintaan 20 % yhteen positioon, 1 % laskennallinen kauppariski.
- D: 10 päivän läpimurto, 30 päivän trendi, enintään 55 %, 2 % laskennallinen kauppariski, aikapoistuminen 15 päivässä.
- E: 15 päivän läpimurto, 50 päivän trendi ja 200 päivän trendisuodatin, enintään 60 %, 2 % laskennallinen kauppariski, aikapoistuminen 30 päivässä.

Kaikki mallien ja osta–pidä-vertailujen ensimmäiset ostot on yhdenmukaistettu vasta 201 valmistuneen päiväkynttilän jälkeen. Tämä estää eriaikaisen markkina-altistuksen aiheuttaman harhan. Mallien säännöt voivat olla historialla ehdollistettuja, joten myöhempää ajanjaksoa ei tule esittää aidosti riippumattomana testinä.

## Uusin läpäisty historiatesti

[GitHub Actions -vertailu](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39770135306), Bitvavon valmistunut BTC-/ETH-/SOL-eurohistoria 2.11.2024–21.10.2026 (719 havaintopäivää), aloitus 5 000 €, osakkeita ei mukana. Laskennalliset kaupankäyntikulut 25 korkopistettä per suunta ja 15 korkopistettä suuntaansa toteutusliukumaa; stressitestissä molemmat kaksinkertaistuvat.

| Malli | Kehitysjakso | Myöhempi jakso | Myöhemmän jakson maksimiarvonlasku | Koko historian loppupääoma arvioidulla realisoitujen voittojen verovarauksella | 2× kulut | Samanaikainen nimellinen stop-riski 3 % |
|---|---:|---:|---:|---:|---:|---:|
| A | −1,65 % | +4,91 % | 4,36 % | 5 158,88 € | 5 020,22 € | 5 158,88 € |
| D | −12,91 % | +25,24 % | 10,32 % | 5 453,68 € | 5 211,88 € | 5 287,42 € |
| E | +2,01 % | +12,57 % | 9,14 % | **5 741,43 €** | **5 657,81 €** | **5 428,78 €** |

**Samanaikainen stop-riski 3 %** tarkoittaa avointen positioiden laskennallisten osto–stop-tappioiden yhteiskattoa uusissa sijoituspäätöksissä; se ei rajoita toteutuvaa enimmäistappiota 3 %:iin, koska kurssihypyt ja toteutuskulut voivat kasvattaa tappion.

Samassa testissä erilliset vertailut:

| Ostetaan ja pidetään | Koko havaintoajan kokonaistuotto | Myöhempi jakso | Suurin arvonlasku | 5 000 €:n loppuarvo |
|---|---:|---:|---:|---:|
| BTC | −22,97 % | +33,99 % | 51,70 % | 3 851,49 € |
| BTC + ETH + SOL (1/3 kuhunkin) | −21,25 % | +36,56 % | 63,82 % | 3 937,73 € |

Osta-ja-pidä-luvut sisältävät simuloidut ostokulut, mutta **eivät loppumyynnin kuluja eivätkä laskennallista luovutusvoittoveroa**, toisin kuin aktiivisten mallien realisoitujen myyntien verovaraus. Tästä syystä nettotuottojen suora vertailu on puutteellinen. Riskitasot ovat erilaiset, sillä swing-strategia voi olla pitkään käteisessä. Osinkoja ei ole (vain spot-kryptot); kryptojen väliset vaihdot voivat synnyttää veroja käytännössä.

Parhaan kehitysjakson tuloksella suhteessa maksimilaskuun valikoitui E, mutta valinta ei ole todistetusti tulevaisuudessa parempi. Historiatestissä oli vain kolme kryptoa ja alle kaksi vuotta; se ei kata luotettavasti useita syklejä.

## Uusi E-mallin aidosti eteenpäin kulkeva paperisalkku

- Erillinen jäädytetyn mallin simulaattori: `swingbot/crypto_e_shadow.py`.
- Oma tilansa: `paper/crypto_e_shadow.json`.
- Julkinen iPhone-näkymään soveltuva kooste: `docs/crypto_e_shadow_summary.json`.
- Käynnistynyt ensimmäisestä uudesta valmistuneesta 21.10.2026 päiväkynttilästä, lähtö 5 000 €, ensimmäisessä kirjauksessa **ei takautuvia kauppoja eikä tuottoa**.
- Päivittäinen päivittäminen perustuu vasta valmistuneisiin kynttilöihin. Hypoteettinen seuraavan päivän avaus toteutetaan viiveellä vasta koko päivän toteutuneiden hintatietojen ollessa saatavilla; kyse ei ole aidosta pörssin demotoimeksiannosta.
- 3 %:n **nimellinen** avoimien stop-riskien yhteisraja, 2 % positioriski, korkeintaan 60 % salkusta yhteen instrumenttiin ja 25 %:n huippuun nähden laskun jälkeen uusien ostojen jäädytys. Todellinen toteutunut tappio voi ylittää nämä arvot.
- Ei vipua, johdannaisia eikä shortteja.
- Vuorokauden hinnat ja kaikki kolme instrumenttia vaaditaan yhtäaikaisesti; virhetilanteessa tilaa ei nollata tai täydennetä keksityillä hinnoilla.
- Päivitystyönkulku: [Crypto E shadow paper GitHub Actions](https://github.com/jaheinone-lang/swing-bot-iphone/actions/workflows/crypto-e-shadow.yml). Tällä hetkellä tutkimushaarassa; päivittäinen GitHub-ajastus aktivoituu vasta, kun työnkulku yhdistetään oletushaaraan.
- Testit: `python -m unittest discover -s tests -v`.

Tutkimusraportin ajaminen paikallisesti: `python -m swingbot.crypto_alpha_research`.

**Huomautus:** tulosluvut eivät ole sijoitusennuste, tuottotakuu tai oikeaa rahaa käsittelevän botin dokumentoitua tulosta. Oikeaa kaupankäyntiä ei käynnistetä automaattisesti. Kaikki raportoitu kauppahistoria on simuloitu, vaikka historialliset markkinahinnat ovat todellisia.


## 30 päivän 5 000 € korkoa korolle / 100 % sijoitusasteen koe (22.10.2026)

**Todellisen historiallisen kurssidatan vertailu** suoritettiin [läpäistyssä GitHub Actions -ajossa](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39778339910). Tässä osatestissä perustettiin jokaista strategiaa varten erillinen 5 000 € kuvitteellinen tili 22.9.2026 ja sijoitettiin vain seuraavien **30 valmistuneen päivän** (22.9.–21.10.2026) signaaleilla. Aikaisempaa hintadataa hyödynnettiin vain signaali-indikaattorien laskentaan. Uutta 200 €/kk lisäsijoitusta **ei** lisätty; ei vipua, ei shorttia. Edellisten kauppojen voitot tai tappiot sekä realisoitujen voittojen verovaraus vaikuttavat automaattisesti seuraavaan panokseen.

| Tutkittu E-malli | 30 päivän tulos, € | Loppupääoma, € | 30 pv lasku huipusta | Keskimäärin sijoitettu % | Päiviä vähintään 95 % sijoitettuna | Ostokauppoja |
|---|---:|---:|---:|---:|---:|---:|
| E60, 60 % positioraja, 2 %/kauppa ja 3 % yhteinen nimellinen stop-riski | −119,41 | 4 880,59 | 3,25 % | 18,96 % | 0 | 3 |
| E100, 100 % positioraja, mutta samat 2 %/kauppa ja 3 % yhteisriskirajat | −119,41 | 4 880,59 | 3,25 % | 18,96 % | 0 | 3 |
| E100 all-in, 100 % positioraja, 100 % nimellinen kauppariskikatto, ei yhteistä stop-riskikattoa, top-1 momentum-osto | **−428,20** | **4 571,80** | **8,56 %** | 53,33 % | 16 | 1 |

**Tärkeä ero:** Pelkkä yksittäisen position 100 % salliminen ei lisää sijoitusastetta, jos volatiliteettiin suhteutettu 2 %:n kauppariski ja 3 %:n yhteinen stop-riskikatto sitovat sijoituskokoa. All-in-koe käytti mahdollisen oston yhteydessä käytännössä kaiken käteisen, mutta ostoja tehtiin vain, kun trendi-/läpimurtosäännöt täyttyivät. Siksi kyseessä ei ole joka päivä 100 % markkinoilla oleva salkku. All-in-kokeessa ykkösmomentum-signaali saa etusijan, sillä pääoma sitoutuu yhteen positioon.

### Sama strategia koko historialla, korkoa korolle

Historiallisen aineiston ajanjakso 2.11.2024–21.10.2026; ensimmäinen sallittu osto yhdenmukaisesti 201 valmistuneen kynttilän jälkeen. Alku 5 000 €, ei lisäsijoituksia:

| Malli | Loppupääoma, € | Kokonaistuotto | Suurin historian arvonlasku |
|---|---:|---:|---:|
| E60, riskirajattu | 5 428,78 | +8,58 % | 8,70 % |
| E100, samat riskirajat | 5 428,78 | +8,58 % | 8,70 % |
| E100 all-in, riskiperusteinen sijoituskokoraja poistettu | 4 642,00 | −7,16 % | 20,27 % |

All-in-strategia oli **myös koko historian testissä huonompi** ja vaihteli voimakkaammin. Tämä ei takaa, että lopputulos olisi sama muilla kuukausilla tai tulevaisuudessa. Historiallisten sääntöjen optimointia tulee välttää.

### Laskentaa koskevat rajaukset

- Mallin ostot tapahtuvat seuraavan historiallisen päivän avauksesta, kun signaali on syntynyt valmistuneesta päiväkynttilästä. Stopin ylittävät kurssihypyt voivat aiheuttaa huomattavia lisätappioita.
- Pääoma- ja salkkukohtaisia kaupparajoja ei voi sekoittaa. 100 % *sijoitettavissa* ei tarkoita 100 % *aina sijoitettuna*.
- Kaikki strategiat käyttävät korkoa korolle -laskentaa: uuden position koko perustuu **senhetkiseen** verovarauksen jälkeiseen salkkuarvoon ja käteiseen, ei alkuperäiseen kiinteään 5 000 €:oon.
- Kulut perustuvat simulaation taker + liukuma -arvioihin, eivät toteutuneisiin toimeksiantoihin. Verovaraus koskee vain realisoituja voittoja, ei kaikkia mahdollisia loppupäivän luovutusvoittoveroja.
- Jatkuvaa E-paperisalkkua **ei muutettu**, eikä tätä all-in-versiota pidä ottaa automaattisesti käyttöön.
