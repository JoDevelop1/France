"""Shared timeline: every visual segment lasts a whole number of musical bars,
so cuts land exactly on the downbeats of the soundtrack."""

BPM = 100
BEAT = 60.0 / BPM
BAR = 4 * BEAT
FPS = 30
W, H = 1920, 1080

# Chord symbols -> (bass midi, triad midi notes)
CHORDS = {
    "Dm": (38, [50, 53, 57, 62]),
    "Bb": (34, [50, 53, 58, 62]),
    "F":  (41, [48, 53, 57, 60]),
    "C":  (36, [48, 52, 55, 60]),
    "D":  (38, [50, 54, 57, 62]),
    "G":  (43, [50, 55, 59, 62]),
    "Em": (40, [52, 55, 59, 64]),
    "Dsus": (38, [50, 55, 57, 62]),
}
LOOP = ["Dm", "Bb", "F", "C"]

CHAPTERS = [
    dict(num="I", name="LA GLOIRE DES ARMES", key="mil", level=2, facts=[
        ("1214", "Bouvines", "Philippe Auguste écrase la coalition impériale."),
        ("1429", "Orléans", "Jeanne d'Arc, 17 ans, libère la ville et relève le royaume."),
        ("1515", "Marignan", "François Ier triomphe en Italie."),
        ("1643", "Rocroi", "Le duc d'Enghien brise les tercios espagnols."),
        ("1781", "Yorktown", "De Grasse et Rochambeau offrent l'indépendance à l'Amérique."),
        ("1792", "Valmy", "« Vive la Nation ! » La Révolution tient tête à l'Europe."),
        ("1805", "Austerlitz", "Le chef-d'œuvre tactique de Napoléon."),
        ("1914", "La Marne", "Les taxis de Paris et le sursaut qui sauve le pays."),
        ("1916", "Verdun", "300 jours d'enfer. « Ils ne passeront pas. »"),
        ("1942", "Bir Hakeim", "Les Français libres de Kœnig tiennent tête à Rommel."),
        ("1944", "Paris libéré", "« Libéré par lui-même, libéré par son peuple. »"),
    ]),
    dict(num="II", name="LE GÉNIE DE LA SCIENCE", key="sci", level=3, facts=[
        ("1637", "Descartes", "Le Discours de la méthode fonde la pensée moderne."),
        ("1783", "Montgolfier", "Premier vol humain de l'Histoire, au-dessus de Paris."),
        ("1789", "Lavoisier", "Naissance de la chimie moderne."),
        ("1795", "Le système métrique", "« À tous les temps, à tous les peuples. »"),
        ("1822", "Champollion", "Il déchiffre les hiéroglyphes égyptiens."),
        ("1826", "Niépce", "La première photographie de l'Histoire."),
        ("1829", "Louis Braille", "Il offre l'écriture aux aveugles du monde entier."),
        ("1885", "Pasteur", "Premier vaccin contre la rage."),
        ("1895", "Frères Lumière", "Le cinématographe : le 7e art est né."),
        ("1911", "Marie Curie", "Deux prix Nobel, dans deux sciences différentes."),
        ("1983", "Institut Pasteur", "Barré-Sinoussi et Montagnier identifient le VIH."),
        ("2020", "Emmanuelle Charpentier", "Prix Nobel pour les ciseaux génétiques CRISPR."),
    ]),
    dict(num="III", name="L'AUDACE DES BÂTISSEURS", key="eng", level=3, facts=[
        ("1144", "L'art gothique", "Né à Saint-Denis, il élève les cathédrales vers le ciel."),
        ("1769", "Cugnot", "Le fardier, premier véhicule automobile de l'Histoire."),
        ("1801", "Jacquard", "Le métier à cartes perforées, ancêtre de l'informatique."),
        ("1869", "Canal de Suez", "Ferdinand de Lesseps relie la Méditerranée à la mer Rouge."),
        ("1886", "La Liberté", "Bartholdi et Eiffel offrent au monde son symbole."),
        ("1889", "Tour Eiffel", "Plus haute structure du monde pendant 41 ans."),
        ("1909", "Louis Blériot", "Première traversée de la Manche en avion."),
        ("1943", "Cousteau & Gagnan", "Le scaphandre autonome ouvre les océans."),
        ("1969", "Concorde", "Le supersonique franco-britannique prend son envol."),
        ("1979", "Ariane", "L'Europe conquiert l'espace depuis Kourou."),
        ("2004", "Viaduc de Millau", "Le pont le plus haut du monde."),
        ("2007", "TGV", "Record du monde sur rail : 574,8 km/h."),
    ]),
    dict(num="IV", name="LA PATRIE DES DROITS", key="soc", level=3, facts=[
        ("1789", "Droits de l'Homme", "« Les hommes naissent et demeurent libres et égaux en droits. »"),
        ("1791", "Émancipation", "Premier pays d'Europe à faire des Juifs des citoyens égaux."),
        ("1804", "Code civil", "Il inspire le droit de dizaines de nations."),
        ("1848", "Abolition", "Victor Schœlcher abolit définitivement l'esclavage."),
        ("1882", "Jules Ferry", "L'école gratuite, laïque et obligatoire."),
        ("1905", "Laïcité", "Séparation des Églises et de l'État."),
        ("1936", "Front populaire", "Les congés payés."),
        ("1944", "Vote des femmes", "Les Françaises deviennent électrices et éligibles."),
        ("1945", "Sécurité sociale", "La solidarité nationale pour tous."),
        ("1948", "René Cassin", "Il co-rédige la Déclaration universelle des droits de l'homme."),
        ("1975", "Simone Veil", "La loi qui donne aux femmes le droit de choisir."),
        ("1981", "Robert Badinter", "Abolition de la peine de mort."),
    ]),
    dict(num="V", name="L'ÉCLAT DE LA CULTURE", key="cul", level=4, facts=[
        ("1664", "Molière", "Tartuffe. La comédie française devient universelle."),
        ("1682", "Versailles", "L'Europe entière imite la cour du Roi-Soleil."),
        ("1748", "Montesquieu", "De l'esprit des lois : la séparation des pouvoirs."),
        ("1751", "L'Encyclopédie", "Diderot et d'Alembert rassemblent le savoir des Lumières."),
        ("1830", "Delacroix", "La Liberté guidant le peuple."),
        ("1862", "Victor Hugo", "Les Misérables."),
        ("1874", "Impressionnisme", "Monet, Renoir, Degas réinventent la peinture."),
        ("1894", "Coubertin", "Il fonde le CIO et ressuscite les Jeux olympiques."),
        ("1903", "Tour de France", "La plus grande course cycliste du monde."),
        ("1946", "Festival de Cannes", "La capitale mondiale du cinéma."),
        ("2010", "Gastronomie", "Le repas gastronomique des Français inscrit à l'UNESCO."),
        ("2018", "Champions du monde", "Deux étoiles sur le maillot bleu."),
    ]),
]


def build():
    segs = []
    t = 0.0

    def add(kind, bars, chords, **kw):
        nonlocal t
        segs.append(dict(kind=kind, start=t, bars=bars, dur=bars * BAR, chords=chords, **kw))
        t += bars * BAR

    add("line", 1, ["Dm"], text="Il y a des pays qui ont une histoire.", level=0)
    add("line", 1, ["Bb"], text="Et puis il y a la France.", level=0)
    add("title", 3, ["Dm", "Bb", "C"], level=1)

    k = 0
    for ch in CHAPTERS:
        add("chapter", 1, ["Dm"], chapter=ch, level=ch["level"])
        for i, (year, title, sub) in enumerate(ch["facts"]):
            add("fact", 1, [LOOP[k % 4]], chapter=ch, year=year, title=title, sub=sub,
                level=ch["level"], index=i)
            k += 1

    all_facts = sorted((f for ch in CHAPTERS for f in ch["facts"]), key=lambda f: int(f[0]))
    n = 32
    picks = [all_facts[round(i * (len(all_facts) - 1) / (n - 1))] for i in range(n)]
    add("flurry", 4, ["Bb", "C", "Dsus", "D"], picks=picks, level=5)
    add("outro", 8, ["G", "D", "Em", "D", "C", "D", "G", "G"], level=6)
    return segs, t


SEGMENTS, TOTAL = build()
