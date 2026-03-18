# 🤖 Tehisintellekti rakendamise projektiplaani mall (CRISP-DM)

<br>
<br>


## 🔴 1. Äritegevuse mõistmine
*Fookus: mis on probleem ja milline on hea tulemus?*


### 🔴 1.1 Kasutaja kirjeldus ja eesmärgid
Kellel on probleem ja miks see lahendamist vajab? Mis on lahenduse oodatud kasu? Milline on hetkel eksisteeriv lahendus?

> **Kasutaja:** Toiduainetööstuse tootmisliini juhid ja operaatorid.
> **Probleem:** Kiire tootmisliin (8 toodet/7 sek), kus inimesed ei jõua visuaalselt kontrollida kõiki vigu (vale silt, puuduv toode, vale kuupäev).
> **Kasu:** Vigade automaatne märkamise võimekus, praagi vähendamine ja täpne statistika kulumaterjalide (kile/sildid) ja tootmisliini efektiivsuse (seisakud, roboti jõudlus) kohta.
> **Hetke lahendus:** Liini lõpus 2 inimest, kes panevad tooteid kasti ja teevad pistelist visuaalset kontrolli.

### 🔴 1.2 Edukuse mõõdikud
Kuidas mõõdame rakenduse edukust? Mida peab rakendus teha suutma?

> **Tuvastamise täpsus:** Mõõdetuna märgendatud testandmestiku põhjal (Ground Truth vs AI ennustus). Süsteem peab tuvastama vale toote, puuduva sildi ja vale kuupäeva.
> **Statistiline võimekus:** Võimekus lugeda tühje pakendeid ja tuvasta sildivahetuse kohti, et arvutada raisatud materjali hulka.
> **Operatiivsus:** Info edastamine reaalajas iga takti kohta, võimaldades kliendil otsustada liini peatamise vajaduse üle.

### 🔴 1.3 Ressursid ja piirangud
Millised on ressursipiirangud (nt aeg, eelarve, tööjõud, arvutusvõimsus)? Millised on tehnilised ja juriidilised piirangud (GDPR, turvanõuded, platvorm)? Millised on piirangud tasuliste tehisintellekti mudelite kasutamisele?

> **Ajaline surve:** Takt on 7 sekundit, pildistamine peab toimuma u 2 sekundit pärast liikumise algust (fookuse saavutamiseks).
> **Andmed:** Valede näidete andmebaas puudub hetkel täielikult.
> **Tehniline:** Kasutatakse 2 kaamerat, hetkel arendus ühe 4-tootelise striimi põhjal. 
> **Juriidiline:** GDPR risk on madal, kuna inimeste nägusid kaamerasse ei jää.

<br>
<br>


## 🟠 2. Andmete mõistmine
*Fookus: millised on meie andmed?*

### 🟠 2.1 Andmevajadus ja andmeallikad
Milliseid andmeid (ning kui palju) on lahenduse toimimiseks vaja? Kust andmed pärinevad ja kas on tagatud andmetele ligipääs?

> **Allikas:** Tootmisliini kohale paigaldatud kaamerate videovoog.
> **Vajadus:** Hetkel töös 4 x 3-minutilist videot. Vajalik on koguda ja märgendada andmeid 4 põhitoote kohta, millele projekt alguses keskendub.
> **Ligipääs:** Olemasolev poolaasta pikkune ajalugu on salvestatud.

### 2.2 Andmete kasutuspiirangud
Kas andmete kasutamine (sh ärilisel eesmärgil) on lubatud? Kas andmestik sisaldab tundlikku informatsiooni?

> Kasutamine on lubatud kliendi huvides. Andmestik ei sisalda tundlikku isikustatud infot (näod puuduvad).

### 🟠 2.3 Andmete kvaliteet ja maht
Millises formaadis andmeid hoiustatakse? Mis on andmete maht ja andmestiku suurus? Kas andmete kvaliteet on piisav (struktureeritus, puhtus, andmete kogus) või on vaja märkimisväärset eeltööd)?

> **Formaat:** Videostriim (MP4/RTSP).
> **Kvaliteet:** Keskmine – esineb liikumisest tingitud udu ja kaadrisse ilmuvad operaatorite käed/kindad. 
> **Struktuur:** Partii pikkus on 10-15 minutit (sildirulli pikkus).

### 2.4 Andmete kirjeldamise vajadus
Milliseid samme on vaja teha, et kirjeldada olemasolevaid andmeid ja nende kvaliteeti.

> Vajalik on märgendada (label):
> 1. Toote piirkond (bounding box).
> 2. Sildi asukoht (lubatud hälve 1 cm).
> 3. Triipkood ja kuupäev.
> 4. Toote tüüp (klassifitseerimiseks).

<br>
<br>


## 🟡 3. Andmete ettevalmistamine
Fookus: Toordokumentide viimine tehisintellekti jaoks sobivasse formaati.

### 🟡 3.1 Puhastamise strateegia
Milliseid samme on vaja teha andmete puhastamiseks ja standardiseerimiseks? Kui suur on ettevalmistusele kuluv aja- või rahaline ressurss?

> **Sünkroonimine:** Optical flow abil tuvastatakse liikumise algus, et teha pilt 2 sekundit hiljem, mil kaamera on fokusseerinud.
> **Vigaste kaadrite ignoreerimine:** Kui analüüs ebaõnnestub (nt käsi ees), märgitakse see takt loetamatuks, mitte veaks.

### 🟡 3.2 Tehisintellektispetsiifiline ettevalmistus
Kuidas andmed tehisintellekti mudelile sobivaks tehakse (nt tükeldamine, vektoriseerimine, metaandmete lisamine)?

> **Tükeldamine:** Üldisest striimist lõigatakse välja 4 eraldi tootepilti vastavalt piirkondadele.
> **OCR:** Tekstituvastus tehakse otse pildilt (OCR mootor tegeleb siseselt puhastamisega).

<br>
<br>

## 🟢 4. Tehisintellekti rakendamine
Fookus: Tehisintellekti rakendamise süsteemi komponentide ja disaini kirjeldamine.

### 🟢 4.1 Komponentide valik ja koostöö
Millist tüüpi tehisintellekti komponente on vaja rakenduses kasutada? Kas on vaja ka komponente, mis ei sisalda tehisintellekti? Kas komponendid on eraldiseisvad või sõltuvad üksteisest (keerulisem agentsem disan)?

> **Komponendid:** > 1. Takti tuvastamine, muutuse tuvastamise kaudu (pikslite mean absolute difference).
> 2. Toote klassifitseerimine (AI - kas on õige toode).
> 3. Sildi detekteerimine (AI - asukoht ja olemasolu).
> 4. Teksti ja triipkoodi lugemine (OCR süsteem).
> Komponendid töötavad jadamisi: taktituvastus -> btriipkood > ROI lõikamine -> OCR ehk kuupäev, siltide olemasolu tuvastamine, toote välimuse alusel klassifitseerimine.

### 🟢 4.2 Tehisintellekti lahenduste valik
Milliseid mudeleid on plaanis kasutada? Kas kasutada valmis teenust (API) või arendada/majutada mudelid ise?

> Plaanis on kasutada lokaalselt majutatud mudeleid, et tagada reaalajas töökiirus ja andmete turvalisus.
* Sildituvastus: DINOv2-small. Teeb pildist vektori. 372 arvu. Sarnase sisuga pildid on selles vektorite ruumis sarnaste vektoritega kujutatud. Kui videovoost tuleva pildiala vektor on näidisega sarnane, siis ütleme, et silt on olemas. 
* Kuupäevatuvastus: me oleme välja lõiganud ala, kus kuupäev peaks olema. Saadame oma 4 kuupäeva-ala mingisse OCR mudelisse. Peab olema kiire!
* Tootetuvastus: pildiala DINOv2-ga enkoodida. Iga toote kohta kogume 10 + näidet = 10 vektorit. Treenime lineaarse mudeli, mis eristaks 5 klassi (4 toodet + empty), sisendiks on vektorid. 

### 🟢 4.3 Kuidas hinnata rakenduse headust?
Kuidas rakenduse arenduse käigus hinnata rakenduse headust?

> Testandmetel põhinev täpsus, saagis (mitu % toodetest suudetakse edukalt analüüsida) ning valehäirete osakaal iga mooduli jaoks eraldi.

### 🟢 4.4 Rakenduse arendus
Milliste sammude abil on plaanis/on võimalik rakendust järk-järgult parandada (viibadisain, erinevte mudelite testimine jne)?

> 1. Algne mudel sildi olemasolu ja asukoha kontrolliks.
> 2. Toote sisu visuaalne klassifitseerimine (vale toode/vale silt).
> 3. Triipkoodi ja kuupäeva lugemise täpsustamine.

### 🟢 4.5 Riskijuhtimine
Kuidas maandatakse tehisintellektispetsiifilisi riske (hallutsinatsioonid, kallutatus, turvalisus)?

> **Vigane lugemine:** Kuupäeva puhul ei nõuta igalt pakilt 100% lugemist, vaid jälgitakse partii ühtsust. Kui lugemine ebaõnnestub (käsi ees), proovitakse järgmist takti. Lõpliku otsuse liini seiskamiseks teeb alati inimene süsteemi väljastatud info põhjal.

<br>
<br>

## 🔵 5. Tulemuste hindamine
Fookus: kuidas hinnata loodud lahenduse rakendatavust ettevõttes/probleemilahendusel?

### 🔵 5.1 Vastavus eesmärkidele
Kuidas hinnata, kas rakendus vastab seatud eesmärkidele?

> Võrdlus kliendi ootustega: kas süsteem suudab reaalajas märgata vigu, mida inimesed hetkel ei jõua, ja kas genereeritav statistika sildivahetuste ning tühjade pakendite kohta on piisavalt täpne protsessi monitoorimiseks.

<br>
<br>

## 🟣 6. Juurutamine
Fookus: kuidas hinnata loodud lahenduse rakendatavust ettevõttes/probleemilahendusel?

### 🟣 6.1 Integratsioon
Kuidas ja millise liidese kaudu lõppkasutaja rakendust kasutab? Kuidas rakendus olemasolevasse töövoogu integreeritakse (juhul kui see on vajalik)?

> Rakendus väljastab iga takti kohta info tuvastatud toote ja sildi staatuse kohta. Kasutaja näeb koondstatistikat ja reaalajas hoiatusi monitooringuekraanil.

### 🟣 6.2 Rakenduse elutsükkel ja hooldus
Kes vastutab süsteemi tööshoidmise ja jooksvate kulude eest? Kuidas toimub rakenduse uuendamine tulevikus?

> Kuna tooteid lisandub pidevalt (30-40+), peab süsteem olema täiendatav uute tootenäidiste ja triipkoodidega. Hooldus sisaldab mudeli perioodilist uuesti treenimist uute silditüüpide lisandumisel.