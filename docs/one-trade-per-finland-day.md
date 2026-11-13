# BTC + ETH – yksi päivänsisäinen kauppa per Suomen päivä

Tutkimuspäivä: 23.10.2026. [Onnistunut GitHub Actions -testi](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39899729794).

## Toteutettu käyttäjän toivoma kaupankäyntisääntö

- Sama yksi yhteinen **5 000 € käteissalkku** BTC-EUR- ja ETH-EUR-kohteille, ei SOL-kauppoja, ei velkavipua.
- Päivän aikana enintään **yksi** osto yhteensä kummankin instrumentin kesken Suomen `Europe/Helsinki`-kalenteripäivää kohti. Myös voitollisen välittömän poistumisen jälkeen seuraava osto on aikaisintaan seuraavana päivänä.
- Osto aikaisintaan **klo 09.00** ja viimeistään ennen **klo 20.00 Suomen aikaa**. Tämä on tutkimuksen oletus, ei käyttäjän erikseen vahvistama optimi.
- Osto vain vahvistetussa nousussa. Tutkimuksessa vertaillaan aiempaa `quality_buy_signal`-signaalia uuteen `confirmed_upward_move`-signaaliin, joka edellyttää 3 perättäistä nousevaa valmistunutta 5 minuutin sulkemishintaa, kohtuullista +0,12–0,90 %:n 15 minuutin nousua ja aiempia trendi-/volatiliteetti-/volyymiehtoja.
- Ostosignaali vahvistetaan vasta **valmistuneella** 5 minuutin kynttilällä; simulointitäyttö vasta seuraavan kynttilän avaushintaan.
- Heti kun position mallinnettu myyntihinta saavuttaa **+1 % kaupankäyntikulujen ja slippagen jälkeen ennen veroja**, koko **100 % positio** myydään, seuraavaa saman päivän kauppaa ei tehdä.
- Tappiotilanteessa **1,5 % raakahinnan stop**, suunniteltu pääoman stop-riski enintään **0,25 % per kauppa**, position koko enintään 20 % salkusta. Gap-/slippage-riskit voivat aiheuttaa isomman tappion.
- Jos kauppa ei pääty tavoite-/stop-hintaan, avoin positio suljetaan **klo 21.55 Suomen aikaa** mallinnetulla 5 minuutin kynttilän avauskurssilla. Yön yli ei pidetä position riskiä tutkimuksen säännöillä.
- Jos stop ja voitontavoite osuvat samaan 5 minuutin kynttilään, simulointi valitsee konservatiivisesti stopin ensin.
- **Ei oikeita toimeksiantoja** eikä pörssiin laitettuja OCO-/TP-/SL-toimeksiantoja. Välitön todellinen myynti on erillinen integraatiovaihe ja vaatii toteutumis-/likviditeettitestit.

## 150 päivän historiallinen vertailu

Yhteiset havaintokynttilät: **43 141**, kelpuutetut 5 minuutin kynttilät: **43 110** yhteensä 17 yhtenäisessä jaksossa. Hintoja ei täytetä aukkojen yli. Jaksojen lopussa avoimet positiot suljetaan viimeiseen havaittuun hintaan oletetuilla myyntikuluilla.

| Skenaario | Ostot | Täyden position +1 % nettovoitot | Muu tavoitettu TP | Stopit | Iltasulut | Loppuarvo | Tuotto | Tuotto 2× kulut |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Vanha laatumalli, useita kauppoja/päivä | 61 | – | 20 puolittaista | 55 | – | 4 669,21 € | −330,79 € (−6,62 %) | −400,17 € (−8,00 %) |
| Päivässä enintään 1, vanha laatusignaali, myy 100 % | 36 | 9 | – | 13 | 14 | 4 832,30 € | −167,70 € (−3,35 %) | −228,04 € (−4,56 %) |
| Päivässä enintään 1, vahvistettu 15 min nousu, myy 100 % | 21 | 6 | – | 5 | 10 | **4 937,63 €** | **−62,37 € (−1,25 %)** | **−106,71 € (−2,13 %)** |

Kaksinkertaisten kulujen stressitesti muutti myös simuloitujen TP-osumien määrää.

**Johtopäätös:** Päiväkohtainen 1 kauppa / täysi kotiutus / vahvistettu nousu vähensi vanhan mallin historiallista tappiota **268,42 €**. Se jäi **silti tappiolle**, joten kannattavaa tuottoetua ei ole osoitettu. Noin 150 päivän aikana vain 21 kauppaa pääsi kaikkein tiukimmalla ostosäännöllä läpi; tämä ei ole päivittäinen tuottolupaus.

Tämä aineisto on jo ollut mukana aikaisemman strategian kehityksessä, joten tulos on jälkikäteen sovitettu / kuvaileva eikä riippumaton uusi testi. Lisäksi kynttilän high-tason koskettaminen ei takaa käytännössä limiittitoimeksiannon täyttymistä. Kulut ovat mallioletuksia, Suomen henkilöverot puuttuvat, ja datakatkojen oletettu pakkolikvidointi aiheuttaa epävarmuutta.

## Koodi

- `swingbot/daytrade_one_per_day.py` – valmis yhden kaupankäyntipäivän sääntö ja nousun vahvistus.
- `swingbot/daytrade_150d_research.py` – yksi yhteinen pääoma sekä 150 päivän kolmen strategian vertailu / 2× kulut.
- `tests/test_daytrade_one_per_day.py` – testaa yhden kaupan/d, 100 % TP:n, stopin, illan pakkosulun, SOL-poissulun ja Suomen aikavyöhykkeen.

Muutoksia ei ole yhdistetty päähaaraan, eikä olemassa olevaan E-forward-paperisalkkuun kosketa.
