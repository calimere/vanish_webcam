# VanishCam — effets de disparition pour webcam

La vidéo est traitée sur votre ordinateur. Elle n'est ni enregistrée ni envoyée à un serveur. La fenêtre d'aperçu et la webcam virtuelle n'affichent que la vidéo et les effets, sans menus, instructions ni texte superposés.

Pour un guide pas à pas en anglais et en italien, consultez le [guide utilisateur](USER_GUIDE_EN_IT.md).

## Premiers pas

1. Double-cliquez sur `AVVIA_LOCALE.bat`.
2. Dans le menu de démarrage, choisissez **Normal Vanish**, **Naruto Vanish**, **Particles** ou **Goku** avec la souris ou les touches `1`, `2`, `3` et `4`.
3. Sortez du champ de la caméra pendant 4 secondes, le temps que l'arrière-plan soit capturé. Le terminal indique quand vous pouvez revenir.

**Normal Vanish :** levez l'index et le majeur en signe V. Le fondu démarre dès que le geste est reconnu et dure environ 3,6 secondes.

**Particles :** faites le même signe V que pour Normal Vanish. Votre silhouette se brise en petits fragments colorés qui dérivent latéralement, comme emportés par le vent. L'effet dure environ 2,1 secondes. La silhouette est capturée une seule fois au début de l'effet pour que la vidéo reste fluide.

**Goku :** tenez l'index et le majeur tendus et joints contre votre front pendant 1 seconde. Des lignes verticales animées, façon bande dessinée, traversent votre silhouette juste avant votre téléportation et persistent brièvement ensuite. Pour réapparaître, baissez la main puis refaites le geste pendant 1 seconde. Le retour utilise l'effet inverse. Si vous interrompez la pose, le compte à rebours repart de zéro. `assets/teleport.MP3` est joué à la disparition comme à la réapparition. Le terminal affiche le compte à rebours de chaque geste. Les touches `V` et `R` sont désactivées dans ce mode : le geste est le seul moyen de disparaître et de réapparaître. Aucun texte n'est superposé à la vidéo.

**Naruto Vanish :** joignez les paumes devant la webcam, doigts côte à côte et non entrelacés. Gardez les deux mains visibles. Dès que le geste est reconnu, vous disparaissez dans un nuage de fumée et un tronc de bois apparaît, tombe et reste visible jusqu'à ce que vous appuyiez sur `R`. Aucun microphone n'est nécessaire. Le mode Naruto utilise `hand_landmarker.task` pour suivre les deux mains. `assets/vanish.MP3` est joué par les haut-parleurs de l'ordinateur au début de la disparition, y compris lorsqu'elle est déclenchée avec `V`. Vous pouvez la redéclencher après avoir appuyé sur `R`.

Pour lancer un mode sans passer par le menu :

```powershell
local_app\AVVIA_LOCALE.bat --mode naruto
local_app\AVVIA_LOCALE.bat --mode normal
local_app\AVVIA_LOCALE.bat --mode particles
local_app\AVVIA_LOCALE.bat --mode goku
```

## Webcam virtuelle et OBS

Si [OBS Studio](https://obsproject.com/) est installé, l'application essaie automatiquement d'ouvrir **OBS Virtual Camera**. Le terminal affiche le nom du périphérique. Utilisez `AVVIA_VIRTUAL.bat` pour exiger une webcam virtuelle. Sélectionnez **OBS Virtual Camera** dans l'application qui doit recevoir la vidéo. La caméra virtuelle d'OBS doit être arrêtée tant que cette application produit sa sortie.

Pour utiliser l'effet dans une scène OBS, lancez `AVVIA_OBS.bat`, ajoutez une source **Capture de fenêtre**, sélectionnez **Webcam - Apercu**, puis démarrez la caméra virtuelle depuis OBS. Vous pouvez aussi utiliser [Unity Capture](https://github.com/schellingb/UnityCapture) comme source vidéo virtuelle distincte :

```powershell
local_app\AVVIA_VIRTUAL.bat --virtual-backend unitycapture
```

OBS ne dispose que d'une seule caméra virtuelle. Ne l'utilisez pas à la fois comme entrée et comme sortie d'OBS. Consultez la [documentation de pyvirtualcam](https://github.com/letmaik/pyvirtualcam#supported-virtual-cameras).

## Commandes

- `ESPACE` : capturer un nouvel arrière-plan.
- `R` : faire réapparaître la personne.
- `V` : déclencher manuellement l'effet du mode sélectionné.
- `F` : activer ou désactiver le plein écran.
- `Q` ou `ÉCHAP` : quitter et libérer les caméras.

Les touches `V` et `R` sont désactivées dans le mode Goku.

Vous pouvez changer la caméra, la résolution et le nombre maximal d'images par seconde de la sortie virtuelle :

```powershell
local_app\AVVIA_LOCALE.bat --camera 1 --width 1280 --height 720 --fps 30
```

Pour diagnostiquer la reconnaissance des gestes sans ajouter de texte à la vidéo, ajoutez `--gesture-debug`. Les informations de diagnostic n'apparaissent que dans le terminal.

## Ressources visuelles

Le [tronc de bois](assets/substitution_log.png) est une illustration originale générée avec ImageGen à partir de l'image fournie comme référence visuelle. La fumée est dessinée en temps réel par `naruto_effect.py` : elle suit la position de la personne et s'adapte à l'échelle de la vidéo. Nous avons aussi envisagé une [planche de sprites de fumée CC0](https://opengameart.org/content/smoke-sprite-sheet), mais l'animation procédurale s'adapte mieux au positionnement dynamique sans ressource supplémentaire. Aucune image ni ressource d'anime n'est incluse dans le projet.

Le mode Goku utilise le [modèle BlazeFace à courte portée de MediaPipe](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/web/vision/README.md) pour estimer la position du front, et `hand_landmarker.task` pour suivre les doigts. La traînée visuelle de la téléportation est dessinée par le code, sans images d'anime.
