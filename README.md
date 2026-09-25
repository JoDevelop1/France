# France — Quinze siècles d'histoire

Vidéo-hommage (1920×1080, 30 fps, ~3 min 18 s) à la gloire de la France : ses victoires militaires, son génie scientifique, ses bâtisseurs, ses conquêtes sociales et son rayonnement culturel.

**Vidéo :** [`france_gloire.mp4`](france_gloire.mp4)

## Structure

| Partie | Contenu |
|---|---|
| Intro | « Il y a des pays qui ont une histoire. Et puis il y a la France. » |
| I. La gloire des armes | Bouvines, Orléans, Marignan, Rocroi, Yorktown, Valmy, Austerlitz, la Marne, Verdun, Bir Hakeim, Libération de Paris |
| II. Le génie de la science | Descartes, Montgolfier, Lavoisier, système métrique, Champollion, Niépce, Braille, Pasteur, Lumière, Marie Curie, VIH, CRISPR |
| III. L'audace des bâtisseurs | Art gothique, Cugnot, Jacquard, Suez, statue de la Liberté, tour Eiffel, Blériot, Cousteau, Concorde, Ariane, Millau, TGV |
| IV. La patrie des droits | Droits de l'Homme, émancipation des Juifs, Code civil, abolition de l'esclavage, école de Jules Ferry, laïcité, congés payés, vote des femmes, Sécurité sociale, René Cassin, loi Veil, abolition de la peine de mort |
| V. L'éclat de la culture | Molière, Versailles, Montesquieu, l'Encyclopédie, Delacroix, Hugo, impressionnisme, Coubertin, Tour de France, Cannes, gastronomie UNESCO, deux étoiles |
| Final | Récapitulatif chronologique de 32 dates, puis *La Marseillaise* : Liberté · Égalité · Fraternité — Vive la France |

Chaque carte dure exactement une mesure de la bande-son (100 BPM), les coupes tombent donc sur les temps forts.

## Tout est généré par code

- `src/timeline.py` — les faits, les chapitres et la grille musicale partagée.
- `src/audio.py` — bande-son orchestrale synthétisée (cordes, cuivres, timbales, percussions, réverbération) avec le premier vers de *La Marseillaise* en final.
- `src/video.py` — rendu des images (Pillow + NumPy) envoyé directement à ffmpeg.

```bash
pip install pillow numpy scipy imageio-ffmpeg
cd src
python3 audio.py      # -> build/soundtrack.wav
python3 video.py      # -> france_gloire.mp4
PREVIEW=15,45,190 python3 video.py   # images fixes dans build/ pour vérifier la mise en page
```
