# Swing Bot 2.0 — maksullisen markkinadatan yksityinen ympäristö

**Tilanne 13.11.2026:** Tämä `jaheinone-lang/swing-bot-iphone` on JULKINEN
GitHub-repositorio. Se saa sisältää botin yleisen lähdekoodin,
julkisista lähteistä saatavaa sallittua tietoa, synteettisiä esimerkkejä
ja turvallisia offline-testejä. Se **ei** ole lisensoidun EODHD-datan,
historian, osakekohtaisten signaalien, API-avainten tai yksityisten
tutkimusraporttien tallennuspaikka.

## Käyttöoikeusraja

EODHD:n henkilökohtainen sopimus sallii omien sijoitusten yksityisen
tutkimuksen, historiatestit ja aineiston säilyttämisen, mutta ei datan
julkaisemista. EODHD kehottaa varmistamaan erikseen myös
**johdettujen tulosten** julkaisemisen oikeudet. Siksi tässä
projektissa EODHD-pohjaiset per osake -signaalit, historialliset kurssit,
raportit ja tulokset käsitellään oletusarvoisesti kaikki yksityisinä.

- Viralliset ehdot: https://eodhd.com/financial-apis/terms-conditions
- Henkilökohtainen käyttö: https://eodhd.com/help/personal-use
- Säilytys tilauksen päätyttyä: https://eodhd.com/help/storage

Lisenssi koskee **henkilökohtaista tutkimusta**, ei osakeyhtiön,
asiakkaiden tai julkisen maksullisen palvelun dataa. Muussa käytössä
varmista sopimus EODHD:lta ensin.

## Erottelu

1. Julkinen `swing-bot-iphone` jatkaa iPhone-näkymää, avointa ohjelmakoodia
   ja offline-testejä. Tähän ei tuoda EODHD:n maksullisia tuloksia.
2. Erillinen **private**-repositorio `swing-bot-private-research` sisältää
   vain yksityisen tutkimuksen ajokoodin, konfiguraation sekä
   käyttöoikeuksiltaan rajatut GitHub Actions -ajot. Salaisuudet asetetaan
   uuden repositorion **Settings → Secrets and variables → Actions**.
3. Varsinaiset markkinadata-arkistot tallennetaan mieluiten paikalliseen
   salattuun datakansioon, salattuun yksityiseen tallennustilaan tai muuhun
   sovittuun pääsyrajattuun varastoon. Älä säilytä pitkiä raakakursseja
   GitHubissa, vaikka repo olisi private: koko, varmuuskopiot ja
   käyttäjä-/järjestelmälokit tarvitsevat erilliset rajat.
4. Yksityinen automaatio ei julkaise aineistoa **GitHub Pagesiin**,
   julkisen repositorion commiteihin, pull requesteihin, Actions-artefakteihin,
   vikavirheviesteihin tai tulosteisiin.
5. Näistä julkisista työnkuluista EODHD-avainta käyttävät vaiheet
   **ohitetaan**, jos `github.event.repository.private != true`.
   Pelkkä `.gitignore` ei ole turvallisuustakuu.

## Yksityisen repositorion luominen kerran käsin

GitHub-yhteydellä käytettävissä olevat tiedostonmuokkaustoiminnot eivät
luo repositorioita, vaihda niiden näkyvyyttä tai aseta Secrets-arvoja.
Siksi omistajan pitää tehdä nämä vaiheet GitHubin käyttöliittymässä:

1. Avaa https://github.com/new — Owner: `jaheinone-lang`;
   Repository name: `swing-bot-private-research`.
2. Valitse **Private** ennen `Create repository` -painiketta.
   Alusta repo README:llä, jotta `main`-haara syntyy.
3. Varmista uuden repositorion etusivulta, että sen nimen vieressä on
   **Private**. Näkyvyyden täytyy olla yksityinen ENNEN data-ajoja.
4. Varmista GitHub-sovelluksen pääsy uuteen repositorioon. Jos sovellus
   on asennettu vain valikoituihin repositorioihin, lisää uusi repo
   GitHubin asennuksen repository access -asetuksissa.
5. Kun koodi on yksityisessä repositoriossa, lisää tarvittaessa sen
   `EODHD_API_TOKEN` Secrets-valikosta. **Älä anna tokenia ChatGPT-viestissä**.
   Pelkkä aiemman julkisen repositorion Secret ei siirry automaattisesti.
6. Yksityisen ajon tulee varmistaa: `repository.private=true`,
   täsmällinen omistaja/repo, henkilökohtainen käyttö, manuaalinen
   hyväksyntä ennen ensimmäistä maksullista hakua,
   pelkät GET-kutsut ja **ei toimeksiantoja**.
7. Varmista ettei GitHub Actions -ajossa julkaista raakaa API-pyyntö-URL:ää,
   sillä EODHD käyttää avainta kyselyparametrissa. Tulosta vain
   sanatyyppinen onnistumis-/virhetila ja turvallinen testikooste.

## Jatkossa rakennettava yksityinen putki

- USA ja Helsinki: vahvistetut EODHD-symbolit, kurssivaluutta,
  yhtiötapahtumat, listautumis-/delistautumispäivät.
- Tiedot haetaan talteen yksityiseen ympäristöön, ja niiden
  lähde/haun päivämäärä kirjataan. Ei keksittyjä puuttuvia arvoja.
- Selvitetään onko point-in-time-osakeuniversumi todella saatavilla.
  Nykyiset aktiiviset ja delistatut listausluettelot **eivät yksin riitä**.
- Testataan etukäteen lukitut strategiat erillisellä
  harjoitus-/validointijaksolla, riippumattomilla pidemmillä vuosilla,
  realistisilla kuluilla ja huonojen markkinavuosien riskillä.
- Vasta riittävän luotettava tutkimus antaa perusteita
  paperikauppaan; tilaus ei anna lupaa oikeisiin kauppoihin.

## Vanhojen julkisten lokien rajoitus

Tämä muutos estää **uudet** EODHD-avainta käyttävät public-Actions-ajot.
Se ei poista GitHub-historiaa, aiempia julkisia Actions-lokeja,
ulkopuolisten klooneja eikä välimuistikopioita. Aiemmat
EODHD-tutkimusraportit voidaan siirtää uusiin yksityisiin raportteihin
ja poistaa julkisesta haarasta, mutta historian täydellinen siivoaminen
on erillinen, vaikutuksiltaan arvioitava toimenpide.
