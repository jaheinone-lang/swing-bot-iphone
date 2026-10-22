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
