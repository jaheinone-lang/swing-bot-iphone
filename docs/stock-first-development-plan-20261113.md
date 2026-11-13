# Swing Bot 2.0 – osakekehityksen tutkimussuunnitelma

Päätös 13.11.2026: uusia kryptokaupankäyntistrategioita ei toistaiseksi kehitetä. BTC/ETH-tutkimus ja vanhat paperitilit säilytetään sellaisinaan. Pääpaino USA:n osakkeissa; EU ja Helsinki seuraavat datan vahvistuessa.

## Tutkimusstrategiat
1. USA small cap momentum: vahva avausgappi, sulku nousuun, poikkeava konsolidoitu vaihto.
2. USA small cap failed gap-up: päivän aikana epäonnistunut nousugappi, vain analyysi; ei shorttia eikä osakelainauksen oletusta.
3. USA large cap breakout: 20 päivän huipun ylitys, 50/200 päivän nousutrendi, 60 päivän momentum.

Nämä ovat itsenäisesti suunniteltuja tutkimushypoteeseja, eivät väitetysti Sampsa Tikkalan julkaisemattomia sääntöjä. Toteutus: swingbot/us_stock_setup_research.py. Testit: tests/test_us_stock_setup_research.py. Kaikki palauttavat vain tarkkailusignaalin, ei kauppakäskyjä.

## Datan laatu ja testin vaatimukset
- Kaikista osakkeista oikeat ja ajankohdan mukaiset historiatiedot, listaus- ja delistaustilanteet, splittikorjaukset, oikea päivävaihto, historiallinen markkina-arvo, split-vahvistukset, spread ja yritystapahtumat.
- Alpaca IEX-only data ei riitä todistamaan koko USA:n vaihtoa, eikä Trading 212 DEMO -metadatan lista ole hintahistoria.
- Ei luotettavaa voittoennustetta pelkistä synteettisistä testeistä; verrataan myöhemmin aktiivista osakestrategiaa passiiviseen indeksisijoitukseen ja käteiseen.
- Erillinen tuleva lukittu datajakso, PnL kulujen jälkeen, max drawdown, osakelainan saatavuus ja shorttikustannukset ennen kaupankäyntiä.

## Raha ja turvallisuus
Treidaussalkun aiempi 5000 EUR lähtöpääoma ja 100 %:n vuosituottotavoite säilyvät; tavoite ei ole ennuste eikä anna lupaa riskin nostoon. Aiempi 200 EUR/kk pitosalkun BTC/ETH-tutkimussuunnitelma ei vaihdu automaattisesti osakkeisiin eikä synnytä oikeaa kuukausisummaa tai toimeksiantoa. Ei vipua, live-ostoja eikä shorttimyyntiä. Strategia E -paperitili on koskematon.

## Status
USA:n kolmen setup-perheen signaalitunnistus ja datan hylkäysportit: toteutettu, synteettiset testit.
Todellisen USA:n small cap -osakehistorian kulujen jälkeinen strategiatesti: tekemättä, vahvistettu historiallinen data ja käyttölupa tarvitaan.
