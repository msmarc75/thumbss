# YouTube Thumbnails Generator

Ce projet permet de générer automatiquement des miniatures YouTube "catchy" à partir de titres de vidéos. Il utilise l'API OpenAI (modèle `gpt-image-1.5`) pour créer des images pertinentes, recadrées au format 16:9 et compressées à moins de 2 Mo.

Le projet propose une interface web simple pour faciliter l'utilisation.

## Fonctionnalités

*   **Génération par IA** : Utilise le modèle `gpt-image-1.5` pour des résultats de haute qualité.
*   **Format YouTube** : Recadrage automatique au format 16:9 (1536x864) pour éviter les bandes noires.
*   **Optimisation** : Compression automatique des images (JPEG) pour une taille inférieure à 2 Mo.
*   **Interface Web** : Interface facile à utiliser pour générer plusieurs miniatures à la fois.
*   **Gestion des erreurs** : Fallback automatique et messages d'erreur clairs.

## Prérequis

*   Python 3.8+
*   Une clé API OpenAI

## Installation

1.  Clonez ce dépôt :
    ```bash
    git clone https://github.com/votre-user/youtube-thumbnails-generator.git
    cd youtube-thumbnails-generator
    ```

2.  Installez les dépendances :
    ```bash
    pip install -r requirements.txt
    ```

3.  Configurez votre clé API OpenAI.
    Créez un fichier `.env` à la racine du projet et ajoutez votre clé :
    ```
    OPENAI_API_KEY=votre_clé_api_ici
    ```

## Utilisation

### Interface Web (Recommandé)

1.  Lancez l'application web :
    ```bash
    python app.py
    ```

2.  Ouvrez votre navigateur et allez à l'adresse : `http://127.0.0.1:5000`

3.  Entrez vos titres de vidéos et cliquez sur "Générer".

### En ligne de commande

Vous pouvez aussi utiliser le script principal directement si vous préférez :

```bash
python youtube_optimizer.py
```

## Structure du projet

*   `app.py` : Application Flask (Backend de l'interface web).
*   `youtube_optimizer.py` : Logique de génération et de traitement d'image.
*   `templates/` : Fichiers HTML pour l'interface web.
*   `static/thumbnails/` : Dossier où sont sauvegardées les miniatures générées.
*   `tests/` : Tests unitaires.

## Tests

Pour lancer les tests :

```bash
python -m unittest discover .
```
