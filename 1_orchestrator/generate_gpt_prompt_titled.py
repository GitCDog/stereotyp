#!/usr/bin/env python3
"""
Erstellt gpt_prompts.txt mit provokanten Titeln fÃ¼r alle Stories ohne Bild.
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
    26:  "Vanlife â€“ Freiheit oder Armut?",
    33:  "Bio-Mami hat immer recht?",
    46:  "5 Minuten frÃ¼her ist pÃ¼nktlich?",
    51:  "Pfandflaschen sammeln ist peinlich?",
    52:  "Kein GerÃ¤usch im Bordbistro â€“ wessen Regel?",
    53:  "Umzugshelfer oder Umzugs-Diktator?",
    54:  "45 Minuten Parkplatz suchen â€“ lohnt das?",
    55:  "Zu viel versichert â€“ geht das Ã¼berhaupt?",
    56:  "Deutsche GrÃ¼ndlichkeit â€“ Fluch oder Segen?",
    57:  "5â‚¬ Kaffee â€“ bist du das wert?",
    58:  "Fensterputzen bis zur Perfektion â€“ normal?",
    59:  "Vereinsausflug â€“ Teambuilding oder Qual?",
    60:  "Handtuch auf Liegestuhl â€“ wessen Platz?",
    61:  "Schimmel abkratzen und aufessen â€“ geht das?",
    62:  "'Wir fahren nachts' â€“ spart das wirklich Zeit?",
    63:  "Wartenummer 247 â€“ wie lange noch?",
    64:  "Bio kaufen â€“ Gewissen oder Geldbeutel?",
    65:  "Tatort-Experte vom Sofa â€“ kennst du das?",
    66:  "Sonntagsspaziergang â€“ wer macht das noch?",
    67:  "Regenradar checken ist ein Hobby?",
    68:  "'Nur gucken' â€“ lÃ¼gen wir uns alle an?",
    69:  "Ist deutsche Wertarbeit noch real?",
    70:  "Kleingarten â€“ Paradies oder GefÃ¤ngnis?",
    71:  "Deutschland faxed noch 2025?",
    72:  "Partnerlook â€“ sÃ¼ÃŸ oder peinlich?",
    73:  "LaubblÃ¤ser am Samstag â€“ ist das Krieg?",
    74:  "Landlust â€“ wer glaubt das noch?",
    75:  "'Wir schenken uns nichts' â€“ stimmt das wirklich?",
    76:  "Bier ist ein Grundnahrungsmittel?",
    77:  "Kreuzfahrt â€“ Traum oder Alptraum?",
    82:  "'Man gÃ¶nnt sich ja sonst nichts' â€“ wirklich?",
    83:  "Feilschen auf dem Flohmarkt â€“ ist das okay?",
    84:  "Ordnung muss sein â€“ oder?",
    85:  "'Darf man das noch sagen?' â€“ darf man?",
    86:  "Das Internet sagt es â€“ also stimmt es?",
    87:  "Parkplatz mit dem KÃ¶rper reservieren â€“ geht das?",
    88:  "FrÃ¼h aufstehen macht erfolgreich?",
    89:  "Wer hat den schÃ¶nsten Adventskranz?",
    90:  "'Das wird man wohl noch sagen dÃ¼rfen' â€“ darf man?",
    91:  "'Ich bin kein Experte, aber...' â€“ wirklich?",
    92:  "'Wir treffen uns bald' â€“ lÃ¼gen wir alle?",
    93:  "'Damals im Ferienlager' â€“ dein Lieblingsthema?",
    94:  "'Das lohnt sich fÃ¼r mich nicht mehr' â€“ wirklich?",
    95:  "'Hab ich's nicht gesagt?' â€“ nervt das?",
    96:  "Smartphone zu modern â€“ gibt's das wirklich?",
    97:  "Kein Konflikt ist auch keine LÃ¶sung?",
    98:  "SchnÃ¤ppchen kaufen oder nur prahlen?",
    99:  "Beziehungen durch GefÃ¤lligkeiten â€“ gesund?",
    100: "'Eigentlich wÃ¤re ich gerne...' â€“ und?",
    103: "Bali Yoga â€“ Erleuchtung oder Instagram?",
    104: "Vibe Coding â€“ ist das noch Programmieren?",
    106: "Betriebsrat â€“ Held oder Blockierer?",
    107: "Porsche â€“ wer braucht das wirklich?",
    108: "Thermomix â€“ kocht er wirklich besser?",
    109: "'Digga' sagen â€“ ist das noch okay?",
    111: "Mops â€“ schÃ¶nste Rasse oder Qual?",
    112: "Klimaaktivismus â€“ hilft das wirklich?",
    113: "DSGVO â€“ schÃ¼tzt das oder nervt das?",
    114: "Pattaya â€“ Urlaub oder Geheimnis?",
    115: "Bierleiche â€“ Held des Abends?",
    116: "Pilates oder doch einfach Yoga?",
    117: "'Mein Nervensystem' â€“ ist das eine Krankheit?",
    119: "Alles eine VerschwÃ¶rung?",
    120: "Bitcoin macht alle reich?",
    123: "Augenbrauenpiercing â€“ noch zeitgemÃ¤ÃŸ?",
    124: "'Mach kein Auge' â€“ was heiÃŸt das?",
    125: "Klopapier â€“ Ã¼ber oder unter?",
    126: "Handschlag â€“ altmodisch oder respektvoll?",
    127: "Haartransplantation TÃ¼rkei â€“ lohnt sich das?",
    128: "Protein in allem â€“ braucht man das?",
    129: "Demeter â€“ teurer oder wirklich besser?",
    130: "Was ist des Deutschen liebstes Kind?",
    131: "Shisha rauchen â€“ harmlos oder gefÃ¤hrlich?",
    132: "'Wir duzen uns jetzt' â€“ wer hat das entschieden?",
    134: "Gebrauchte UnterwÃ¤sche kaufen â€“ geht das?",
    135: "Tinder â€“ findet man da wirklich Liebe?",
    136: "Tinder Guys â€“ alle gleich?",
    137: "Das Tinder-Foto lÃ¼gt?",
    139: "GNTM â€“ Model oder Trauma?",
    140: "Gym Girls â€“ trainieren oder posten?",
    141: "Gym Guys â€“ Sport oder Ego?",
    142: "Hyrox â€“ Sport oder SelbstbeschÃ¤ftigung?",
    143: "Enge Hosen bei MÃ¤nnern â€“ geht das?",
    144: "Bachata â€“ Tanz oder Anmache?",
    145: "Bachata tanzen â€“ Kunst oder Flirt?",
    146: "Twerken â€“ Kunst oder zu viel?",
    149: "Kiffen ist gesund?",
    150: "Deutschrap â€“ Kunst oder LÃ¤rm?",
    156: "Viele kleine Tattoos â€“ Trend oder Fehler?",
    157: "Veganes Steak â€“ schmeckt das wirklich?",
    158: "Papierstrohhalm rettet die Welt?",
    165: "Facelift â€“ mutig oder traurig?",
    166: "Schlauchboot-Lippen â€“ schÃ¶n oder nicht?",
    178: "Techno â€“ Musik oder LÃ¤rm?",
    179: "Love Parade â€“ war das die beste Zeit?",
    180: "Buffaloschuhe sind zurÃ¼ck?",
    181: "Klimakleben â€“ Held oder Verbrecher?",
    189: "Hauptschule â€“ noch eine Chance?",
    190: "Realschule â€“ der goldene Mittelweg?",
    191: "Gymnasium â€“ Privileg oder Pflicht?",
    192: "Waldorfschule â€“ Quatsch oder Zukunft?",
    193: "Privatschule â€“ Bildung oder Status?",
    194: "Gesamtschule â€“ die LÃ¶sung fÃ¼r alle?",
    195: "Sonderschule â€“ FÃ¶rderung oder Ausgrenzung?",
    196: "Berufsschule â€“ unterschÃ¤tzt?",
    197: "Home Office â€“ Segen oder Fluch?",
    198: "Schwarzarbeit â€“ macht das jeder?",
    202: "Wer ist der Aggressivste im Autoscooter?",
    203: "Bierzelt â€“ Kultur oder Chaos?",
    204: "JGA Bauchladen â€“ wer kauft das?",
    205: "Sonntag im Garten â€“ Pflicht oder Freiheit?",
    206: "Karma â€“ glaubst du daran?",
    207: "Wahlversprechen â€“ werden die gehalten?",
    208: "Kurzarmhemd â€“ modisch oder nicht?",
    209: "Karohemd â€“ HolzfÃ¤ller oder Hipster?",
    210: "Ist deutsche Bolognese eine Beleidigung?",
    211: "IKEA-Sonntag â€“ Pflicht fÃ¼r Deutsche?",
    212: "Lidl â€“ schÃ¤mst du dich?",
    213: "Aldi-Mittelgang â€“ wer kauft das wirklich?",
    214: "Rewe â€“ zu teuer dafÃ¼r?",
    215: "Edeka â€“ wo kaufst du wirklich ein?",
    216: "Spar â€“ gibt es den noch?",
    217: "Norma â€“ wer geht da hin?",
    218: "Tegut â€“ zu bio fÃ¼r dich?",
    219: "Penny â€“ peinlich oder praktisch?",
    220: "Netto â€“ der unterschÃ¤tzte Discounter?",
    221: "Corona war alles gelogen?",
    222: "Long Covid â€“ gibt es das wirklich?",
    223: "Bist du krank oder Hypochonder?",
    224: "FuÃŸball verbindet â€“ oder eskaliert?",
    225: "GÃ¤rtnern ist das neue Yoga?",
    226: "BierkÃ¶nig â€“ Kult oder Peinlichkeit?",
    227: "Trichter trinken â€“ ist das noch lustig?",
    228: "Ein JÃ¤gerbomb â€“ und dann?",
    233: "FIFA zÃ¤hlt als Sport?",
    235: "Negerkuss umbenennen â€“ muss das sein?",
    236: "Deutschland faxed noch?",
    237: "Ruhetag am Sonntag â€“ wer braucht das noch?",
    238: "Bohren nach 22 Uhr â€“ ist das erlaubt?",
    239: "Reinheitsgebot â€“ heilig oder Ã¼berholt?",
    240: "Nackt in der Sauna â€“ oder mit Badehose?",
    241: "Kollegen in der Sauna â€“ nein danke?",
    242: "Kaffee und Kuchen â€“ Pflicht am Sonntag?",
    243: "Helene Fischer â€“ Kult oder Kitsch?",
    244: "Warum lÃ¤uft Florian Silbereisen Ã¼berall?",
    245: "Gartenzwerg â€“ Kulturgut oder Geschmacksproblem?",
    246: "Antifa â€“ Held oder Chaot?",
    247: "Politisch korrekt â€“ wer entscheidet das?",
    248: "IG Metall streikt â€“ wer zahlt das?",
    249: "Fasching â€“ muss das sein?",
    250: "Karneval â€“ Pflicht in KÃ¶ln?",
    251: "Wandteller â€“ wer hÃ¤ngt die noch auf?",
    252: "SchultÃ¼te â€“ deutsches Kulturgut?",
    253: "Kuckucksuhr â€“ kitschig oder Kulturgut?",
    254: "Camping â€“ Urlaub oder Strafe?",
    255: "Spaghettieis ist eine deutsche Erfindung?",
    256: "DÃ¶ner macht schÃ¶ner â€“ stimmt das?",
    257: "Flohmarkt â€“ Schatz oder SondermÃ¼ll?",
    258: "Sozialstaat â€“ wer zahlt den eigentlich?",
    259: "AuslÃ¤nder willkommen â€“ oder doch nicht?",
    260: "Hartz IV â€“ Schande oder Sicherheit?",
    261: "Spritpreise â€“ wer ist schuld?",
    262: "Warum zahlen wir so viele Steuern?",
    263: "Sechs Monate auf den Handwerker warten â€“ normal?",
    264: "Arbeitsamt â€“ Hilfe oder DemÃ¼tigung?",
    265: "TÃ¼ren mit dem Ellbogen aufmachen â€“ macht das jeder?",
    266: "Energiewende â€“ klappt das wirklich?",
    267: "GrÃ¼ne Energie â€“ zu teuer fÃ¼r uns?",
    268: "SperrmÃ¼ll â€“ Schatz oder MÃ¼ll?",
    269: "Atomkraft â€“ war das ein Fehler?",
    270: "Schrebergarten â€“ Freiheit oder GefÃ¤ngnis?",
    271: "Balkonien â€“ der gÃ¼nstigste Urlaub?",
    272: "Warum fahren alle nach Bibione?",
    273: "Silvesterknaller verbieten â€“ ja oder nein?",
    274: "Spieleabend â€“ macht das noch SpaÃŸ?",
    275: "Mensch Ã¤rgere dich nicht â€“ oder doch?",
    276: "Brettspiele â€“ das Comeback des Jahres?",
    277: "Gesellschaftsabend â€“ Pflicht oder Freiwillig?",
    278: "Kolleg:innen schreiben â€“ muss das sein?",
    279: "WorÃ¼ber reden Deutsche beim Small Talk?",
    280: "Hundemama â€“ Hund oder Kind?",
    281: "Deutscher Schlager â€“ peinlich oder ehrlich?",
    282: "MÃ¼sli â€“ gesÃ¼nder als du denkst?",
    283: "Braucht man wirklich Supplements?",
    284: "Feierabendbier â€“ verdient oder nicht?",
    285: "Datenschutz â€“ interessiert das noch jemanden?",
    286: "Heizkosten â€“ wer zahlt das noch?",
    287: "E-Scooter â€“ MobilitÃ¤t oder Stolperfalle?",
    288: "Deutsche Bahn â€“ kommt der Zug?",
    289: "'Ja ja' â€“ Zustimmung oder Ablehnung?",
    290: "5â‚¬ fÃ¼r GlÃ¼hwein â€“ ist das normal?",
    291: "Wer darf Ã¼ber das Stadtbild entscheiden?",
    296: "FrÃ¼hstÃ¼ck ans Bett â€“ wer macht das noch?",
    298: "BÃ¼rgergeld â€“ zu viel oder zu wenig?",
    299: "Die Linke â€“ noch relevant?",
    300: "650.000â‚¬ fÃ¼r ein grÃ¼nes Auto?",
    # Alle weiteren Stories
    1:   "Funktionsjacke im Urlaub â€“ wer tut das wirklich?",
    2:   "Deutsche sind unhÃ¶flich oder einfach ehrlich?",
    3:   "Tatort verpassen â€“ ist das erlaubt?",
    4:   "StoÃŸlÃ¼ften â€“ rettet das wirklich die Wohnung?",
    5:   "Hausschuhe fÃ¼r GÃ¤ste â€“ Ã¼bertrieben oder normal?",
    6:   "'Haben wir immer so gemacht' â€“ ist das ein Argument?",
    7:   "Dienst ist Dienst â€“ und sonst gar nichts?",
    8:   "47 Ordner fÃ¼r 3 Dokumente â€“ wer macht das?",
    9:   "3 Minuten zu spÃ¤t â€“ ist die Freundschaft vorbei?",
    10:  "Laminieren â€“ wer braucht das wirklich?",
    11:  "Deutsches Brot ist das beste der Welt?",
    12:  "Warum schÃ¼tten Deutsche Wasser in alles?",
    13:  "6 Wochen Spargel â€“ ist das normal?",
    14:  "Kaltes Brot zum Abendessen â€“ wer isst das freiwillig?",
    15:  "Rot ist rot â€“ auch wenn kein Auto kommt?",
    16:  "Zu direkt fÃ¼r dein zartes Ego?",
    17:  "Das Auto als Heiligtum â€“ geht das noch?",
    18:  "MÃ¼lltrennung â€“ Pflicht oder Extremsport?",
    20:  "Ohne Verein kein Leben â€“ wirklich?",
    21:  "Mallorca Kegelclub â€“ Kult oder Peinlichkeit?",
    22:  "Sandalen mit Socken â€“ schÃ¶n oder nicht?",
    23:  "Wandergruppe â€“ wer macht das freiwillig?",
    27:  "E-Auto â€“ Zukunft oder Bevormundung?",
    28:  "Fitness-Influencer aus dem Dorf â€“ wer glaubt dem?",
    29:  "Dein Nachbar meldet alles â€“ ist das okay?",
    30:  "'Die Anzeige ist raus' â€“ wer tut das wirklich?",
    31:  "Deutsche Bahn â€“ wer rastet da nicht aus?",
    32:  "Grillmeister â€“ darf das jeder sein?",
    34:  "Feierabendbier â€“ Recht oder Privileg?",
    35:  "Oktoberfest â€“ Kultur oder Touristenfalle?",
    36:  "Sparkasse â€“ noch zeitgemÃ¤ÃŸ?",
    37:  "Kehrwoche â€“ wer kontrolliert das?",
    38:  "Treppenhaus-Zettel â€“ harmlos oder KriegserklÃ¤rung?",
    39:  "'Mahlzeit!' â€“ was soll das bedeuten?",
    40:  "Durchzug â€“ gefÃ¤hrlich oder Einbildung?",
    41:  "Kassenband â€“ wer packt schnell genug?",
    42:  "'Tja' â€“ was bedeutet das wirklich?",
    43:  "Zu viele Schilder â€“ oder immer noch zu wenig?",
    44:  "'Wo kommen Sie eigentlich her?' â€“ darf man das fragen?",
    45:  "Baumarkt Samstag â€“ warum alle gleichzeitig?",
    47:  "'Haben wir das schriftlich?' â€“ nervt das?",
    48:  "Sonntagsruhe â€“ Gesetz oder EinschrÃ¤nkung?",
    49:  "Fahrradweg-Sheriff â€“ Held oder NervensÃ¤ge?",
    50:  "Alles versichern â€“ Ã¼bertrieben oder klug?",
    51:  "'Ich hab's passend' â€“ wer macht das noch?",
    78:  "Kein Netz im Zug â€“ wessen Schuld?",
    79:  "'FrÃ¼her war alles besser' â€“ wirklich?",
    80:  "'Darf ich mal kurz vorbei?' â€“ was kommt danach?",
    81:  "Schnitzel â€“ groÃŸ genug oder nie groÃŸ genug?",
    101: "Wer ist der Talahon wirklich?",
    102: "Wehrdienst verweigern â€“ feige oder mutig?",
    105: "Chaya erklÃ¤rt dir die Welt â€“ hÃ¶rst du zu?",
    110: "3 Katzen, Bio-Futter, kein Partner â€“ zufrieden?",
    118: "Longevity â€“ lebst du ewig oder stirbst du gesund?",
    121: "Gendern â€“ notwendig oder Unsinn?",
    122: "Arschgeweih â€“ wer hat das noch?",
    133: "OnlyFans â€“ mutig oder verzweifelt?",
    138: "Tinder Date â€“ wer zahlt das?",
    147: "Verliebt in den DJ â€“ ist das okay?",
    148: "DJ Fan Guy â€“ tanzen oder nur stehen?",
    151: "Bootsschuhe ohne Boot â€“ warum?",
    152: "Zu alt fÃ¼r Skaterklamotten?",
    153: "Mama und Tochter in der Disko â€“ wer ist peinlich?",
    154: "Alle tragen den gleichen Rucksack und nennen es Stil?",
    155: "20 Kaffee am Tag â€“ Sucht oder Lebensstil?",
    159: "Pornosucht â€“ redet keiner drÃ¼ber?",
    160: "Unfall gaffen â€“ warum tun wir das?",
    161: "Botox mit 30 â€“ mutig oder traurig?",
    162: "Botox bei MÃ¤nnern â€“ geht das?",
    163: "Vegan, plastikfrei, moralisch Ã¼berlegen?",
    164: "SilikonbrÃ¼ste â€“ selbstbewusst oder unsicher?",
    167: "Fake LV â€“ wer merkt den Unterschied?",
    168: "TikTok-Sucht â€“ wer gibt es zu?",
    169: "Instagram-Sucht â€“ wer ist das nicht?",
    170: "Hipster 2025 â€“ gibt es die noch?",
    171: "Jutebeutel rettet die Welt?",
    172: "Rocker â€“ ausgestorben oder untergetaucht?",
    173: "Biker grÃ¼ÃŸen sich â€“ warum eigentlich?",
    174: "SilberlÃ¶ffel im Mund â€“ merkt man das?",
    175: "Gammler â€“ Freiheit oder Faulheit?",
    176: "GEZ â€“ zahlt das noch jemand freiwillig?",
    177: "TechnomÃ¤dchen â€“ schlÃ¤ft sie nie?",
    182: "CDU â€“ konservativ oder verstaubt?",
    183: "SPD â€“ wÃ¤hlt das noch jemand?",
    184: "FDP â€“ fÃ¼r wen ist die eigentlich?",
    185: "GrÃ¼ne â€“ fÃ¼r die Umwelt oder fÃ¼r sich selbst?",
    186: "AFD wÃ¤hlen â€“ was steckt dahinter?",
    187: "Junge Union â€“ jung und konservativ?",
    188: "Deutsche BÃ¼rokratie â€“ Weltmeister?",
    199: "Baustelle in Deutschland â€“ wann ist die fertig?",
    200: "Tankstelle â€“ das teuerste Fast Food?",
    201: "Boxautomat â€“ wer nutzt das wirklich?",
    229: "Erwachsene auf Steckenpferden â€“ das ist ernst gemeint?",
    230: "Smart Home â€“ schlauer als du?",
    231: "Rasierte Arme bei MÃ¤nnern â€“ geht das?",
    232: "Kein Augenkontakt beim AnstoÃŸen â€“ 7 Jahre schlechter Sex?",
    234: "Ist deutsche KÃ¼che wirklich gut?",
    292: "DSDS ist seit 20 Jahren tot â€“ die Fans nicht?",
    293: "Alles toxisch â€“ wer entscheidet das?",
    294: "People Pleaser â€“ bist du das?",
    295: "Basic Bee â€“ peinlich oder ehrlich?",
    297: "Merz als Bundeskanzler â€“ wirklich?",
    301: "Kennt ihr das â€“ ohne Eastpak warst du in den 90ern nobody?",
    302: "Wer rettet die Welt â€“ oder nur sein Image?",
    303: "Wachsen Frauen mit Nagel Tips wirklich Ã¼ber sich hinaus?",
    304: "Warum ist die DÃ¶nerbude Deutschlands heiligste Institution?",
    305: "Ist das wirklich das beste Essen nach Mitternacht?",
    306: "Warum darf jeder deinen KÃ¶rper kommentieren auÃŸer du?",
    307: "Kennt ihr den echten Grund fÃ¼r 'Ja Schatz' in Deutschland?",
    308: "Kennst du den Satz, der jede Emotion sofort killt?",
    309: "Warum trÃ¤gt halb Deutschland dieselben hÃ¤sslichen Sandalen?",
    310: "Warum rasiert sich der Deutsche fÃ¼r 25â‚¬ im Barber Shop?",
    311: "DÃ¼rfen Deutsche eigentlich Dreads tragen?",
    312: "Warum zahlen Deutsche fÃ¼r absichtlichen Schmerz?",
    313: "Warum reiÃŸen sich Deutsche freiwillig Haare mit Kuchenzutaten?",
    314: "Bist du der Laser-Alman oder bleibst du beim Epilieren?",
    315: "Warum bucht der Deutsche Urlaub nur um den Pool zu sichern?",
    316: "Warum fliegen Deutsche zum Haare kleben nach Istanbul?",
    317: "Wer kennt diesen Socken-Friedhof neben dem Bett?",
    318: "Darf der ZDF einfach lÃ¼gen?",
    319: "Ist er schon zu alt?",
    320: "Nur in Deutschland â€“ Ventilator statt Klimaanlage",
    321: "WÃ¼rde Heidi unser Land kaputt machen?",
    322: "Und, wie lÃ¤ufts in der Dachgeschosswohnung?",
    323: "Lohnt sich die SelbstÃ¤ndigkeit in D Ã¼berhaupt?",
    331: "Was ist der Unterschied zwischen Zoo und CSD â€“ Jens Spahn weiÃŸ es",
    2100: "Wer heiÃŸt Luce â€“ und warum kennt sie ihren Namen-Buchstabierdienst besser als jeder Kundenberater?",
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

        text = story_file.read_text(encoding="utf-8").strip()
        text = re.sub(r"\s+", " ", text)

        if 2000 <= nr_int <= 2099:
            lines.append(
                f'{nr_int}. erstelle ein portrait-bild (1024x1536) im Stil einer modernen flachen Illustration. '
                f'Zeige eine Person passend zum deutschen Namen "{stereotyp}" und zur folgenden Story. '
                f'Die Person soll realistisch und unscheinbar aussehen â€“ kein model, kein idealtyp, normaler alltags-mensch. '
                f'Oben links nur den Namen "{stereotyp}" in grosser, dunkler moderner Schrift â€“ kein weiterer Text im Bild, kein Titel. '
                f'Hintergrund: organische abstrakte Formen in gedaempften Farben, passend zur Stimmung der Story. '
                f'Die Person, Mimik, Kleidung, Koerpersprache und Hintergrundfarben sollen die Story widerspiegeln. '
                f'Stil: cleane Vektor-Illustration, warme PastelltÃ¶ne. Story: "{text}"'
            )
        else:
            title = TITLES.get(nr_int, stereotyp)
            lines.append(
                f'{nr_int}. erstelle ein bild (1024x1536) dazu, nicht dÃ¼ster und nicht bÃ¶se '
                f'und nehme nicht so viel text in das bild rein, '
                f'stelle realistische alltagsmenschen dar â€“ keine models, keine attraktiven idealtypen, '
                f'normale kÃ¶rper, verschiedene altersgruppen (20-65 jahre), unscheinbares aussehen wie echte deutsche, '
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

