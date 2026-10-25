# BTC + ETH: viiden vuoden ostojen 15–120 minuutin hintapolut

**GitHub Actions onnistui:** https://github.com/jaheinone-lang/swing-bot-iphone/actions/runs/40117589113

Tutkimus käyttää 23.10.2021–22.10.2026 julkisia Bitvavo BTC/ETH 5 min kynttilöitä. Lukittu `morning_strict`-ostosignaali, yhteinen 5000 € käteissalkku, enintään yksi osto Suomen kalenteripäivässä. Osto seuraavan 5 min avauksessa, lopuksi stop / 100 % position +1 % nettotavoite / klo21.55 sulku. Kuluarviot sisältyvät realisoituihin PnL-tuloksiin, eivät alla oleviin **raakahinnan muutoksiin**.

## Varmennetut kaupat

- 50 ostoa. Näistä 17 saavutti +1 %:n kulujen jälkeisen kokonaisposition kotiutuksen (FULL_TP), 27 päättyi stop-lossiin, 6 muuhun sulkuun. Loppu 5000 → 4749,60 €, yhteensä −250,40 € ennen veroja.
- BTC: 19 ostoa, 5 FULL_TP, −122,45 €. ETH: 31 ostoa, 12 FULL_TP, −127,97 €. Pieni otos, osumisprosenttien arviovälit menevät päällekkäin.

## Oston jälkeiset hinnat, prosenttia simuloituun ostohintaan nähden

| Mittaus | FULL_TP, keskiarvo (n) | STOP, keskiarvo (n) |
|---|---:|---:|
| 15 min | +0,175 % (17) | −0,076 % (27) |
| 30 min | +0,020 % (16) | −0,250 % (27) |
| 60 min | +0,058 % (16) | −0,224 % (26) |
| 120 min | +0,187 % (14) | −0,237 % (23) |

**Metodiikan rajoitus:** nämä hinnat on kirjattu vain, jos kauppa oli yhä avoinna kyseisen 5 min kynttilän loppuessa. Aiemmin poistuneet puuttuvat mittarista (survivorship censoring). Lisäksi 5 min OHLC-kynttilöiden sisäinen tapahtumajärjestys on epäselvä. Historiallista keskiarvoa EI voi käyttää suoraan tulevan oston voittoennusteena.

## Ostoa edeltäneet, valmistuneesta kynttilästä tunnetut signaalipiirteet

| Tunnus | FULL_TP (17) | STOP (27) |
|---|---:|---:|
| 15min nousu ennen ostoa | +0,569 % | +0,652 % |
| 4h uudemman ja vanhemman trendijakson ero | +2,045 % | +1,776 % |
| Signaalikynttilän volyymi / edellisen 20 kynttilän keskiarvo | 3,379× | 3,381× |

- Voittavien kauppojen pidempi trendi oli keskimäärin hieman vahvempi, mutta aineisto on vain 17 vs 27 tapausta, eikä aineistosta voi ilman riippumatonta lisätestiä asettaa luotettavaa 4h-trendirajaa.
- STOP-kaupoissa ennen ostoa oli itse asiassa hieman voimakkaampi 15min nousu: mahdollinen hintapiikin ja ylikuumenemisen merkki, **ei** todistettu ennuste.
- Suhteellinen volyymi oli käytännössä sama: volyymi yksin ei ollut erotteleva muuttuja.
- Avoimen kaupan jälkeen 15–30 minuutin aikana tapahtuvat muutokset voivat toimia tulevaisuudessa vain **positionhallinnan** päätöstekijöinä, eivät aiemman oston syynä.

## Kriittinen vertailu aiempaan riskiin

Aiempi viiden vuoden `timeout_120m`-tutkimus **ei** parantanut strategiaa kannattavaksi: loppusaldo 4766,13 € ja tulos −233,87 € (vanha −250,40 €). Vastaavasti 30min heikkenemispoisto −248,76 €. Tähän analyysiin perustuva uusi 30min pakkosulku voisi leikata myös myöhemmin onnistuneita kauppoja. Siksi **ei vielä uutta exit-sääntöä käyttöönottoon**.

## Seuraava varmennus

- Lukitse tutkimusversion alkuperäiset ostot ja poistumiset; kerää täysin uutta forward-only-paperidata-aineistoa (hintakynttilät, tarjouskirjan paras bid/ask ja toimeksiannon täyttymisolettamat).
- Älä käytä edellä esitettyjä onnistumisten jälkikäteisiä eroja automaattiseen optimointiin samalla viiden vuoden datalla.
- Arvioi erillinen ennalta määritelty 30min early-loss -sääntö VASTA jatkossa, kontrolliryhmään verrattuna, kulut ja stopin gap-riskit mukana.

**Ei oikeita toimeksiantoja, ei muutoksia aiempaan E-paperisalkkuun.**
