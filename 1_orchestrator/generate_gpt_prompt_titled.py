#!/usr/bin/env python3
"""
Erstellt gpt_prompts.txt mit provokanten Titeln für alle Stories ohne Bild.
Ausgabe: C:\\Users\\slawa\\OneDrive\\8_stereotypen\\gpt_prompts.txt
"""

import re
from pathlib import Path
import input_reader as ir

STORIES_DIR = Path("1_input")
INPUT_FILE = "1_input/1_input_file.txt"
OUT = Path(r"C:\Users\slawa\OneDrive\8_stereotypen\gpt_prompts.txt")

# Provokante Titel pro Story-Nr (plain integer als Key)
TITLES = {
    19:  "Bargeld ist Freiheit?",
    24:  "Mein Handtuch, mein Platz?",
    25:  "Techno ist eine Religion?",
    26:  "Vanlife – Freiheit oder Armut?",
    33:  "Bio-Mami hat immer recht?",
    46:  "5 Minuten früher ist pünktlich?",
    51:  "Pfandflaschen sammeln ist peinlich?",
    52:  "Kein Geräusch im Bordbistro – wessen Regel?",
    53:  "Umzugshelfer oder Umzugs-Diktator?",
    54:  "45 Minuten Parkplatz suchen – lohnt das?",
    55:  "Zu viel versichert – geht das überhaupt?",
    56:  "Deutsche Gründlichkeit – Fluch oder Segen?",
    57:  "5€ Kaffee – bist du das wert?",
    58:  "Fensterputzen bis zur Perfektion – normal?",
    59:  "Vereinsausflug – Teambuilding oder Qual?",
    60:  "Handtuch auf Liegestuhl – wessen Platz?",
    61:  "Schimmel abkratzen und aufessen – geht das?",
    62:  "'Wir fahren nachts' – spart das wirklich Zeit?",
    63:  "Wartenummer 247 – wie lange noch?",
    64:  "Bio kaufen – Gewissen oder Geldbeutel?",
    65:  "Tatort-Experte vom Sofa – kennst du das?",
    66:  "Sonntagsspaziergang – wer macht das noch?",
    67:  "Regenradar checken ist ein Hobby?",
    68:  "'Nur gucken' – lügen wir uns alle an?",
    69:  "Ist deutsche Wertarbeit noch real?",
    70:  "Kleingarten – Paradies oder Gefängnis?",
    71:  "Deutschland faxed noch 2025?",
    72:  "Partnerlook – süß oder peinlich?",
    73:  "Laubbläser am Samstag – ist das Krieg?",
    74:  "Landlust – wer glaubt das noch?",
    75:  "'Wir schenken uns nichts' – stimmt das wirklich?",
    76:  "Bier ist ein Grundnahrungsmittel?",
    77:  "Kreuzfahrt – Traum oder Alptraum?",
    82:  "'Man gönnt sich ja sonst nichts' – wirklich?",
    83:  "Feilschen auf dem Flohmarkt – ist das okay?",
    84:  "Ordnung muss sein – oder?",
    85:  "'Darf man das noch sagen?' – darf man?",
    86:  "Das Internet sagt es – also stimmt es?",
    87:  "Parkplatz mit dem Körper reservieren – geht das?",
    88:  "Früh aufstehen macht erfolgreich?",
    89:  "Wer hat den schönsten Adventskranz?",
    90:  "'Das wird man wohl noch sagen dürfen' – darf man?",
    91:  "'Ich bin kein Experte, aber...' – wirklich?",
    92:  "'Wir treffen uns bald' – lügen wir alle?",
    93:  "'Damals im Ferienlager' – dein Lieblingsthema?",
    94:  "'Das lohnt sich für mich nicht mehr' – wirklich?",
    95:  "'Hab ich's nicht gesagt?' – nervt das?",
    96:  "Smartphone zu modern – gibt's das wirklich?",
    97:  "Kein Konflikt ist auch keine Lösung?",
    98:  "Schnäppchen kaufen oder nur prahlen?",
    99:  "Beziehungen durch Gefälligkeiten – gesund?",
    100: "'Eigentlich wäre ich gerne...' – und?",
    103: "Bali Yoga – Erleuchtung oder Instagram?",
    104: "Vibe Coding – ist das noch Programmieren?",
    106: "Betriebsrat – Held oder Blockierer?",
    107: "Porsche – wer braucht das wirklich?",
    108: "Thermomix – kocht er wirklich besser?",
    109: "'Digga' sagen – ist das noch okay?",
    111: "Mops – schönste Rasse oder Qual?",
    112: "Klimaaktivismus – hilft das wirklich?",
    113: "DSGVO – schützt das oder nervt das?",
    114: "Pattaya – Urlaub oder Geheimnis?",
    115: "Bierleiche – Held des Abends?",
    116: "Pilates oder doch einfach Yoga?",
    117: "'Mein Nervensystem' – ist das eine Krankheit?",
    119: "Alles eine Verschwörung?",
    120: "Bitcoin macht alle reich?",
    123: "Augenbrauenpiercing – noch zeitgemäß?",
    124: "'Mach kein Auge' – was heißt das?",
    125: "Klopapier – über oder unter?",
    126: "Handschlag – altmodisch oder respektvoll?",
    127: "Haartransplantation Türkei – lohnt sich das?",
    128: "Protein in allem – braucht man das?",
    129: "Demeter – teurer oder wirklich besser?",
    130: "Was ist des Deutschen liebstes Kind?",
    131: "Shisha rauchen – harmlos oder gefährlich?",
    132: "'Wir duzen uns jetzt' – wer hat das entschieden?",
    134: "Gebrauchte Unterwäsche kaufen – geht das?",
    135: "Tinder – findet man da wirklich Liebe?",
    136: "Tinder Guys – alle gleich?",
    137: "Das Tinder-Foto lügt?",
    139: "GNTM – Model oder Trauma?",
    140: "Gym Girls – trainieren oder posten?",
    141: "Gym Guys – Sport oder Ego?",
    142: "Hyrox – Sport oder Selbstbeschäftigung?",
    143: "Enge Hosen bei Männern – geht das?",
    144: "Bachata – Tanz oder Anmache?",
    145: "Bachata tanzen – Kunst oder Flirt?",
    146: "Twerken – Kunst oder zu viel?",
    149: "Kiffen ist gesund?",
    150: "Deutschrap – Kunst oder Lärm?",
    156: "Viele kleine Tattoos – Trend oder Fehler?",
    157: "Veganes Steak – schmeckt das wirklich?",
    158: "Papierstrohhalm rettet die Welt?",
    165: "Facelift – mutig oder traurig?",
    166: "Schlauchboot-Lippen – schön oder nicht?",
    178: "Techno – Musik oder Lärm?",
    179: "Love Parade – war das die beste Zeit?",
    180: "Buffaloschuhe sind zurück?",
    181: "Klimakleben – Held oder Verbrecher?",
    189: "Hauptschule – noch eine Chance?",
    190: "Realschule – der goldene Mittelweg?",
    191: "Gymnasium – Privileg oder Pflicht?",
    192: "Waldorfschule – Quatsch oder Zukunft?",
    193: "Privatschule – Bildung oder Status?",
    194: "Gesamtschule – die Lösung für alle?",
    195: "Sonderschule – Förderung oder Ausgrenzung?",
    196: "Berufsschule – unterschätzt?",
    197: "Home Office – Segen oder Fluch?",
    198: "Schwarzarbeit – macht das jeder?",
    202: "Wer ist der Aggressivste im Autoscooter?",
    203: "Bierzelt – Kultur oder Chaos?",
    204: "JGA Bauchladen – wer kauft das?",
    205: "Sonntag im Garten – Pflicht oder Freiheit?",
    206: "Karma – glaubst du daran?",
    207: "Wahlversprechen – werden die gehalten?",
    208: "Kurzarmhemd – modisch oder nicht?",
    209: "Karohemd – Holzfäller oder Hipster?",
    210: "Ist deutsche Bolognese eine Beleidigung?",
    211: "IKEA-Sonntag – Pflicht für Deutsche?",
    212: "Lidl – schämst du dich?",
    213: "Aldi-Mittelgang – wer kauft das wirklich?",
    214: "Rewe – zu teuer dafür?",
    215: "Edeka – wo kaufst du wirklich ein?",
    216: "Spar – gibt es den noch?",
    217: "Norma – wer geht da hin?",
    218: "Tegut – zu bio für dich?",
    219: "Penny – peinlich oder praktisch?",
    220: "Netto – der unterschätzte Discounter?",
    221: "Corona war alles gelogen?",
    222: "Long Covid – gibt es das wirklich?",
    223: "Bist du krank oder Hypochonder?",
    224: "Fußball verbindet – oder eskaliert?",
    225: "Gärtnern ist das neue Yoga?",
    226: "Bierkönig – Kult oder Peinlichkeit?",
    227: "Trichter trinken – ist das noch lustig?",
    228: "Ein Jägerbomb – und dann?",
    233: "FIFA zählt als Sport?",
    235: "Negerkuss umbenennen – muss das sein?",
    236: "Deutschland faxed noch?",
    237: "Ruhetag am Sonntag – wer braucht das noch?",
    238: "Bohren nach 22 Uhr – ist das erlaubt?",
    239: "Reinheitsgebot – heilig oder überholt?",
    240: "Nackt in der Sauna – oder mit Badehose?",
    241: "Kollegen in der Sauna – nein danke?",
    242: "Kaffee und Kuchen – Pflicht am Sonntag?",
    243: "Helene Fischer – Kult oder Kitsch?",
    244: "Warum läuft Florian Silbereisen überall?",
    245: "Gartenzwerg – Kulturgut oder Geschmacksproblem?",
    246: "Antifa – Held oder Chaot?",
    247: "Politisch korrekt – wer entscheidet das?",
    248: "IG Metall streikt – wer zahlt das?",
    249: "Fasching – muss das sein?",
    250: "Karneval – Pflicht in Köln?",
    251: "Wandteller – wer hängt die noch auf?",
    252: "Schultüte – deutsches Kulturgut?",
    253: "Kuckucksuhr – kitschig oder Kulturgut?",
    254: "Camping – Urlaub oder Strafe?",
    255: "Spaghettieis ist eine deutsche Erfindung?",
    256: "Döner macht schöner – stimmt das?",
    257: "Flohmarkt – Schatz oder Sondermüll?",
    258: "Sozialstaat – wer zahlt den eigentlich?",
    259: "Ausländer willkommen – oder doch nicht?",
    260: "Hartz IV – Schande oder Sicherheit?",
    261: "Spritpreise – wer ist schuld?",
    262: "Warum zahlen wir so viele Steuern?",
    263: "GEZ – zahlst du das freiwillig?",
    264: "Arbeitsamt – Hilfe oder Demütigung?",
    265: "Türen mit dem Ellbogen aufmachen – macht das jeder?",
    266: "Energiewende – klappt das wirklich?",
    267: "Grüne Energie – zu teuer für uns?",
    268: "Sperrmüll – Schatz oder Müll?",
    269: "Atomkraft – war das ein Fehler?",
    270: "Schrebergarten – Freiheit oder Gefängnis?",
    271: "Balkonien – der günstigste Urlaub?",
    272: "Warum fahren alle nach Bibione?",
    273: "Silvesterknaller verbieten – ja oder nein?",
    274: "Spieleabend – macht das noch Spaß?",
    275: "Mensch ärgere dich nicht – oder doch?",
    276: "Brettspiele – das Comeback des Jahres?",
    277: "Gesellschaftsabend – Pflicht oder Freiwillig?",
    278: "Kolleg:innen schreiben – muss das sein?",
    279: "Worüber reden Deutsche beim Small Talk?",
    280: "Hundemama – Hund oder Kind?",
    281: "Deutscher Schlager – peinlich oder ehrlich?",
    282: "Müsli – gesünder als du denkst?",
    283: "Braucht man wirklich Supplements?",
    284: "Feierabendbier – verdient oder nicht?",
    285: "Datenschutz – interessiert das noch jemanden?",
    286: "Heizkosten – wer zahlt das noch?",
    287: "Sprit wird teurer – und dann?",
    288: "Deutsche Bahn – kommt der Zug?",
    289: "'Ja ja' – Zustimmung oder Ablehnung?",
    290: "5€ für Glühwein – ist das normal?",
    291: "Wer darf über das Stadtbild entscheiden?",
    296: "Frühstück ans Bett – wer macht das noch?",
    298: "Bürgergeld – zu viel oder zu wenig?",
    299: "Die Linke – noch relevant?",
    300: "650.000€ für ein grünes Auto?",
    # Alle weiteren Stories
    1:   "Funktionsjacke im Urlaub – wer tut das wirklich?",
    2:   "Deutsche sind unhöflich oder einfach ehrlich?",
    3:   "Tatort verpassen – ist das erlaubt?",
    4:   "Stoßlüften – rettet das wirklich die Wohnung?",
    5:   "Hausschuhe für Gäste – übertrieben oder normal?",
    6:   "'Haben wir immer so gemacht' – ist das ein Argument?",
    7:   "Dienst ist Dienst – und sonst gar nichts?",
    8:   "47 Ordner für 3 Dokumente – wer macht das?",
    9:   "3 Minuten zu spät – ist die Freundschaft vorbei?",
    10:  "Laminieren – wer braucht das wirklich?",
    11:  "Deutsches Brot ist das beste der Welt?",
    12:  "Warum schütten Deutsche Wasser in alles?",
    13:  "6 Wochen Spargel – ist das normal?",
    14:  "Kaltes Brot zum Abendessen – wer isst das freiwillig?",
    15:  "Rot ist rot – auch wenn kein Auto kommt?",
    16:  "Zu direkt für dein zartes Ego?",
    17:  "Das Auto als Heiligtum – geht das noch?",
    18:  "Mülltrennung – Pflicht oder Extremsport?",
    20:  "Ohne Verein kein Leben – wirklich?",
    21:  "Mallorca Kegelclub – Kult oder Peinlichkeit?",
    22:  "Sandalen mit Socken – schön oder nicht?",
    23:  "Wandergruppe – wer macht das freiwillig?",
    27:  "E-Auto – Zukunft oder Bevormundung?",
    28:  "Fitness-Influencer aus dem Dorf – wer glaubt dem?",
    29:  "Dein Nachbar meldet alles – ist das okay?",
    30:  "'Die Anzeige ist raus' – wer tut das wirklich?",
    31:  "Deutsche Bahn – wer rastet da nicht aus?",
    32:  "Grillmeister – darf das jeder sein?",
    34:  "Feierabendbier – Recht oder Privileg?",
    35:  "Oktoberfest – Kultur oder Touristenfalle?",
    36:  "Sparkasse – noch zeitgemäß?",
    37:  "Kehrwoche – wer kontrolliert das?",
    38:  "Treppenhaus-Zettel – harmlos oder Kriegserklärung?",
    39:  "'Mahlzeit!' – was soll das bedeuten?",
    40:  "Durchzug – gefährlich oder Einbildung?",
    41:  "Kassenband – wer packt schnell genug?",
    42:  "'Tja' – was bedeutet das wirklich?",
    43:  "Zu viele Schilder – oder immer noch zu wenig?",
    44:  "'Wo kommen Sie eigentlich her?' – darf man das fragen?",
    45:  "Baumarkt Samstag – warum alle gleichzeitig?",
    47:  "'Haben wir das schriftlich?' – nervt das?",
    48:  "Sonntagsruhe – Gesetz oder Einschränkung?",
    49:  "Fahrradweg-Sheriff – Held oder Nervensäge?",
    50:  "Alles versichern – übertrieben oder klug?",
    51:  "'Ich hab's passend' – wer macht das noch?",
    78:  "Kein Netz im Zug – wessen Schuld?",
    79:  "'Früher war alles besser' – wirklich?",
    80:  "'Darf ich mal kurz vorbei?' – was kommt danach?",
    81:  "Schnitzel – groß genug oder nie groß genug?",
    101: "Wer ist der Talahon wirklich?",
    102: "Wehrdienst verweigern – feige oder mutig?",
    105: "Chaya erklärt dir die Welt – hörst du zu?",
    110: "3 Katzen, Bio-Futter, kein Partner – zufrieden?",
    118: "Longevity – lebst du ewig oder stirbst du gesund?",
    121: "Gendern – notwendig oder Unsinn?",
    122: "Arschgeweih – wer hat das noch?",
    133: "OnlyFans – mutig oder verzweifelt?",
    138: "Tinder Date – wer zahlt das?",
    147: "Verliebt in den DJ – ist das okay?",
    148: "DJ Fan Guy – tanzen oder nur stehen?",
    151: "Bootsschuhe ohne Boot – warum?",
    152: "Zu alt für Skaterklamotten?",
    153: "Mama und Tochter in der Disko – wer ist peinlich?",
    154: "Alle tragen den gleichen Rucksack und nennen es Stil?",
    155: "20 Kaffee am Tag – Sucht oder Lebensstil?",
    159: "Pornosucht – redet keiner drüber?",
    160: "Unfall gaffen – warum tun wir das?",
    161: "Botox mit 30 – mutig oder traurig?",
    162: "Botox bei Männern – geht das?",
    163: "Vegan, plastikfrei, moralisch überlegen?",
    164: "Silikonbrüste – selbstbewusst oder unsicher?",
    167: "Fake LV – wer merkt den Unterschied?",
    168: "TikTok-Sucht – wer gibt es zu?",
    169: "Instagram-Sucht – wer ist das nicht?",
    170: "Hipster 2025 – gibt es die noch?",
    171: "Jutebeutel rettet die Welt?",
    172: "Rocker – ausgestorben oder untergetaucht?",
    173: "Biker grüßen sich – warum eigentlich?",
    174: "Silberlöffel im Mund – merkt man das?",
    175: "Gammler – Freiheit oder Faulheit?",
    176: "GEZ – zahlt das noch jemand freiwillig?",
    177: "Technomädchen – schläft sie nie?",
    182: "CDU – konservativ oder verstaubt?",
    183: "SPD – wählt das noch jemand?",
    184: "FDP – für wen ist die eigentlich?",
    185: "Grüne – für die Umwelt oder für sich selbst?",
    186: "AFD wählen – was steckt dahinter?",
    187: "Junge Union – jung und konservativ?",
    188: "Deutsche Bürokratie – Weltmeister?",
    199: "Baustelle in Deutschland – wann ist die fertig?",
    200: "Tankstelle – das teuerste Fast Food?",
    201: "Boxautomat – wer nutzt das wirklich?",
    229: "Erwachsene auf Steckenpferden – das ist ernst gemeint?",
    230: "Smart Home – schlauer als du?",
    231: "Rasierte Arme bei Männern – geht das?",
    232: "Kein Augenkontakt beim Anstoßen – 7 Jahre schlechter Sex?",
    234: "Ist deutsche Küche wirklich gut?",
    292: "DSDS ist seit 20 Jahren tot – die Fans nicht?",
    293: "Alles toxisch – wer entscheidet das?",
    294: "People Pleaser – bist du das?",
    295: "Basic Bee – peinlich oder ehrlich?",
    297: "Merz als Bundeskanzler – wirklich?",
}


def _nr_str(nr: str) -> str:
    return f"{int(str(nr).strip()):04d}"


def find_story_file(nr: str, stereotyp: str = "") -> Path | None:
    ns = _nr_str(nr)
    SKIP = {"00_sammelsurium.txt", "gpt_prompts.txt"}
    matches = [p for p in STORIES_DIR.glob(f"{ns}_*.txt") if p.name not in SKIP]
    return matches[0] if matches else None


def main():
    rows = ir.read_rows(INPUT_FILE)
    lines = []
    skipped = 0
    missing = []

    for row in rows:
        nr_raw = row["nr"].strip()
        nr_int = int(nr_raw)
        stereotyp = row["stereotyp"].strip()

        if row.get("status_story") != "X":
            skipped += 1
            continue

        if row.get("status_pic") == "X":
            skipped += 1
            continue

        story_file = find_story_file(nr_raw)
        if not story_file:
            missing.append(f"#{nr_int} {stereotyp}")
            skipped += 1
            continue

        title = TITLES.get(nr_int, stereotyp)
        text = story_file.read_text(encoding="utf-8").strip()
        text = re.sub(r"\s+", " ", text)

        lines.append(
            f'{nr_int}. erstelle ein bild (1024x1536) dazu, nicht düster und nicht böse '
            f'und nehme nicht so viel text in das bild rein, '
            f'Titel "{title}". Story: "{text}"'
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(lines), encoding="utf-8")
    print(f"[+] {len(lines)} Prompts -> {OUT}")
    if skipped:
        print(f"[*] {skipped} uebersprungen")
    if missing:
        print(f"[!] {len(missing)} Stories ohne Text-Datei (muss zuerst generiert werden):")
        for m in missing:
            print(f"    {m}")


if __name__ == "__main__":
    main()
