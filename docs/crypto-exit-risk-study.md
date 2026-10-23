# BTC + ETH: stop-lossin, kotiutuksen ja kulujen vertailu

Tutkimuspäivä 23.10.2026. Kaikki skenaariot käyttävät yhtä yhteistä 5 000 € BTC/ETH-paperisalkkua ja vanhaa ostojen laatufiltteriä. **Ei välittäjätoimeksiantoja, ei live-kauppaa, ei nykyisen E-paperisalkun muutoksia.**

[GitHub Actions -tutkimusajo](https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/39898033559), testit läpäisty.

## Menetelmä

- 150 päivän Bitvavon EUR-pörssin viiden minuutin kynttilät, BTC ja ETH, 43 141 yhteistä kynttilää. Katkojen yli ei täytetä hintoja.
- Vain yhtenäiset katkojaksot (17 alkuperäistä), harjoitusjakso vanhemmat 90 päivää (13 kelpuutettua segmenttiä) ja myöhemmät 60 päivää (5 segmenttiä).
- Jaksojen tutkimussalkut aloittavat **erillisestä 5 000 €:sta**; saman jakson hyväksyttyjen segmenttien välillä salkun loppusaldo siirtyy, mutta katkojen kohdalla positiot oletetaan suljetuiksi edellisen segmentin viimeiseen hintaan.
- Läpimurto-ostot vasta sulkeutuneen 5 min kynttilän perusteella ja seuraavalla avauskurssilla, 160 kynttilän lämmittely. Stop ennen take-profitia epäselvässä kynttilässä.
- Enintään 0,25 % tilistä suunniteltua nimellistä riskiä/kauppa, 0,5 % samanaikaista nimellistä riskisaldoa, max 20 % varoista yhteen positioon, ei velkavipua.
- Normaali kulumalli: osto ja myynti erikseen 0,25 % kaupankäyntikulu + 0,15 % oletettu liukuma. Kaksinkertaisilla kuluilla kumpikin 0,50 % + 0,30 %.
- Voitollisen kotiutuksen tuotto **kaupankäyntikulujen jälkeen, ennen henkilöveroja**, vähintään 1 % tai 2 % myydyn position kustannuspohjasta. Puolikas positio vs. koko positio.
- Kuusi ehdokasta määritelty ennen tämän tutkimusajon myöhemmän jakson tuloksia. Hyväksytty koulutusvoittaja edellyttäisi vähintään 20 ostoa ja positiivista saldoa sekä normaalikuluilla että kaksinkertaisilla kuluilla.

## Nettotulos euroina, vertailujakson *oma* 5 000 € lähtösaldo

| Stop | Nettotavoite | Myyty osuus | Vanhemmat 90 pv | Myöhemmät 60 pv | Vanhemmat 90 pv 2x kulut | Myöhemmät 60 pv 2x kulut |
|---|---|---|---:|---:|---:|---:|
| 1,5 % | 1 % | 50 % | −156,28 € | −194,52 € | −209,76 € | −212,47 € |
| 0,8 % | 1 % | 50 % | −200,19 € | −294,35 € | −288,31 € | −325,29 € |
| 2,5 % | 1 % | 50 % | −160,50 € | −140,00 € | −185,21 € | −141,84 € |
| 1,5 % | 2 % | 50 % | −128,82 € | −186,70 € | −184,09 € | −208,54 € |
| 1,5 % | 1 % | 100 % | −178,31 € | −250,50 € | −259,44 € | −267,97 € |
| 1,5 % | 2 % | 100 % | −148,02 € | −219,37 € | −224,98 € | −244,43 € |

**Yksikään malli ei täyttänyt harjoitusjakson positiivisen tuoton ja kulustressin hyväksymisehtoja.** Järjestelmä ei siis automaattisesti valinnut mitään mallia käyttöönottoon. Myöhemmän 60 päivän jakson paremman näköistä vaihtoehtoa ei saa nimetä voittajaksi jälkikäteen.

## Havainnot

1. Kapea stop (0,8 %) heikensi tällä aineistolla salkun tulosta suhteessa 1,5 %:iin; todennäköisesti liian paljon normaaleja hinnan heilahduksia suhteessa kuluihin.
2. Leveä stop (2,5 %) pärjäsi myöhemmän jakson negatiivisista vaihtoehdoista vähiten heikosti, mutta oli silti tappiollinen. Ei valittu.
3. Täyden position kotiutus 1 %:n nettotavoitteessa ei ratkaissut kannattavuutta. 2 %:n tavoite paransi osaa harjoitusjakson tuloksista mutta myöhemmässä jaksossa edelleen tappioita.
4. Alkuperäisen mallin 50 %:n kotiutus tuottaa noin 2,70 € voittoa 5 000 € pääomaan nähden tavallisessa ostossa, kun täysi suunniteltu stop voi maksaa 12,50 €. Tällaisia osavoittoja vaaditaan noin viisi yhden tappion kattamiseen, ellei jäljelle jäävä positio tuota lisää.
5. Tämä ei ole riippumaton prospektiivinen koesarja: aiempaa 150 päivän historiaa on käytetty strategian ideoimiseen. Rahoituksen suunnittelu vaatii erillisen eteenpäin kulkevan paperikaupan.

## Täsmennykset

Nämä ovat mallilaskelmia. Käytettyyn dataan liittyy puuttuvia viiden minuutin jaksoja, eikä niissä voi todentaa tosielämän toimeksiantotäyttöjä. Korkojen, tilisiirtojen, pääomatuloverojen, tarjouskirjan spreadien sekä gap-/latenssihäviöiden täydellistä vaikutusta ei ole varmennettu. Ilmoitetut stop-riskit ovat tavoitteita, eivät tappiotakuita. Myös 1 %:n netto on vain onnistuneen myynnin tavoite, ei päivätuottonäkymä.
