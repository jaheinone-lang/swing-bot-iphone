# BTC + ETH: varhaisen poistumisen kokeilu 5 vuoden aineistolla

Kehityspäivä 23.10.2026. **Vain tutkimusversio, ei oikeaa kaupankäyntiä.**

## Mitä muutettiin?

Aiempi viiden vuoden BTC/ETH-tutkimus (23.10.2021–22.10.2026) päätyi tiukimmalla aamupäivän ostosignaalilla 5 000 € -> **4 749,60 €**, eli **−250,40 €** ennen veroja; kaksinkertaisilla kuluilla 4 652,59 €, eli −347,41 €. Aikaisemman mallin tappiot osoittivat, ettei vahva ostosignaali tai 1 % nettovoiton tavoite yksin riitä.

Ostosignaali säilyy täsmälleen ennallaan: vain BTC-EUR tai ETH-EUR, yksi päiväosto Suomen kalenteripäivässä, klo 09–14 vahvistetussa nousussa; poikkeuksellinen volyymi ja pidempi trendi; yksi yhteinen 5 000 € salkku. Onnistuneen position koko määrä 100 % myydään mallin +1 % kulujen jälkeisessä nettotavoitteessa. Positio suljetaan stoppiin tai viimeistään klo 21.55. Stop-riski alussa nimellisesti 0,25 % / kauppa, ei vipua.

Lisätty **valinnainen**, täysin pois päältä oleva alkuperäisessä vertailussa poistumissääntö. Kolme **etukäteen määriteltyä hypoteesia** verrattuna vanhaan poistumiseen:

| Tutkimusmalli | Uusi poistumisehto |
|---|---|
| unchanged | Alkuperäinen stop, tavoite ja iltasulku ennallaan |
| fade_30m | Vähintään 30 minuuttia omistusta, kolme aiempaa sulkua laskee peräkkäin, viimeisin sulku alle 12 kynttilän keskiarvon ja kauppa olisi ennen veroja miinuksella arvioitujen peruskulujen jälkeen |
| timeout_120m | Vähintään 120 minuuttia omistusta ja viimeisimmän valmiin kynttilän laskennallinen nettotulos olisi miinuksella |
| fade_or_timeout | Kumpi tahansa yllä olevista ehdoista |

- Varhainen myynti tapahtuu vasta seuraavan 5 minuutin kynttilän avauskurssiin. Ehtoon ei saa käyttää kyseisen kynttilän tulevaa ylintä/alinta/sulkemishintaa.
- Avoimessa hinnan laskugapissa stop ratkaistaan ennen varhaista myyntiä; hinnan avaaminen nettotavoitteen yli puolestaan ratkaistaan tavoitehintaan.
- Kaikissa simulaatioissa osto- ja myyntikulut sekä arvioitu slippage, lisäksi 2x kulustressi. Suomen henkilöverot eivät sisälly.
- Indikaattorien tutkimus käyttää ainoastaan valmiita kynttilöitä. Datan aukoissa ei keksitä hintoja, vaan jaksot erotellaan. Tämä ei vastaa täydellistä aidon toimeksiantohistorian replayta.
- Yhtäkään uutta sääntöä **ei hyväksytä automaattisesti live-kauppaan** menneen historian perusteella. Vanhat vuodet eivät ole enää täysin riippumaton testidatasetti.
- Koodi: `swingbot/intraday_early_exits.py`, `swingbot/five_year_early_exit_research.py`, lisätty valinnainen `exit_guard` moduuliin `swingbot/daytrade_one_per_day.py`; yksikkötestit `tests/test_intraday_early_exits.py`.

## Viiden vuoden tulosten todentaminen

Tulosraportti julkaistaan vain, kun [GitHub Actions -viiden vuoden tutkimusajo](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39916642825) on todella suorittanut latauksen ja testit onnistuneesti. Jos ajo on kesken tai epäonnistuu, aiemmat lähtötilanteen tulokset säilyvät vain historiallisena vertailukohtana.

**Lähde:** Bitvavon BTC-EUR ja ETH-EUR julkiset viiden minuutin kynttilät; tavoitehinnan koskettaminen ei takaa todellista toimeksiannon täyttöä. Ei avattuja oikeita toimeksiantoja eikä aiempaan E-paperisalkkuun tehtyjä muutoksia.
