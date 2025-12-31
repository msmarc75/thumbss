import os
import requests
import base64
import io
import uuid
import re
from openai import OpenAI, AuthenticationError
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

class YoutubeOptimizer:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("L'API Key OpenAI n'est pas définie. Veuillez définir la variable d'environnement OPENAI_API_KEY.")
        
        self.client = OpenAI(api_key=self.api_key)

    def sanitize_filename(self, title):
        """
        Sanitizes the title to be safe for filenames.
        """
        # Remove invalid characters
        filename = re.sub(r'[\\/*?:"<>|]', "", title)
        # Replace spaces with underscores or dashes if preferred, but spaces are usually fine in modern FS
        # Let's keep spaces but strip leading/trailing
        filename = filename.strip()
        # Limit length to avoid FS issues
        filename = filename[:200]
        return filename

    def process_and_compress_image(self, img_content, output_path, title=None, max_size_mb=2.0):
        """
        Crops the image to 16:9 aspect ratio and compresses.
        """
        try:
            image = Image.open(io.BytesIO(img_content))
            
            # Convert to RGB (in case of RGBA from PNG)
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            
            # Crop to 16:9 Aspect Ratio
            width, height = image.size
            target_ratio = 16 / 9
            current_ratio = width / height
            
            if abs(current_ratio - target_ratio) > 0.01:
                print(f"       Recadrage de l'image au format 16:9...")
                if current_ratio < target_ratio:
                    # Image is too tall/narrow (e.g., 3:2), crop height
                    new_height = int(width / target_ratio)
                    top = (height - new_height) // 2
                    bottom = top + new_height
                    image = image.crop((0, top, width, bottom))
                else:
                    # Image is too wide, crop width
                    new_width = int(height * target_ratio)
                    left = (width - new_width) // 2
                    right = left + new_width
                    image = image.crop((left, 0, right, height))

            # Compression loop
            quality = 95
            while True:
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality, optimize=True)
                size_mb = len(buffer.getvalue()) / (1024 * 1024)
                
                if size_mb < max_size_mb or quality <= 10:
                    with open(output_path, 'wb') as f:
                        f.write(buffer.getvalue())
                    print(f"       Image sauvegardée : {size_mb:.2f} Mo (Qualité: {quality})")
                    break
                
                quality -= 5
                
            return output_path
        except Exception as e:
            print(f"Erreur lors du traitement de l'image : {e}")
            # Fallback: write original content if processing fails
            with open(output_path, 'wb') as f:
                f.write(img_content)
            return output_path

    def generate_thumbnail(self, title, output_path):
        """
        Génère une miniature pour la vidéo via l'API OpenAI et la sauvegarde localement.
        """
        try:
            # Catchy prompt for high CTR, strictly no text or logos
            prompt = f"A viral, click-bait style YouTube thumbnail for the subject: '{title}'. Vivid colors, expressive, high impact, professional photography style, 4k resolution. NO TEXT, NO LOGOS."
            
            response = self.client.images.generate(
                model="gpt-image-1-mini",
                prompt=prompt,
                size="1024x1024",
                # quality="standard", # Not sure if supported by this model, default to implicit
                n=1,
            )
            
            image_data = response.data[0]
            
            if hasattr(image_data, 'url') and image_data.url:
                # Download the image from URL
                img_content = requests.get(image_data.url).content
            elif hasattr(image_data, 'b64_json') and image_data.b64_json:
                # Decode base64 image
                img_content = base64.b64decode(image_data.b64_json)
            else:
                raise ValueError("L'API n'a retourné ni URL ni données base64 pour l'image.")

            # Save, crop and compress
            # title=None disables the text overlay as requested
            return self.process_and_compress_image(img_content, output_path, title=None)
            
        except AuthenticationError as e:
            print(f"Erreur d'authentification : Votre clé API est invalide. Veuillez vérifier votre fichier .env.")
            raise e
        except Exception as e:
            print(f"Erreur lors de la génération de la miniature pour '{title}': {e}")
            return None

    def process_videos(self, titles, output_dir="thumbnails", use_uuids=True, progress_callback=None):
        """
        Traite une liste de titres: génère une miniature pour chaque titre.
        If use_uuids is False, uses sanitized titles for filenames.
        progress_callback: function(current_index, total, title)
        """
        results = []
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        print(f"Traitement de {len(titles)} vidéos...")
        total = len(titles)

        try:
            for i, title in enumerate(titles, 1):
                if progress_callback:
                    progress_callback(i, total, title)

                print(f"\n[{i}/{total}] Titre: {title}")
                
                if use_uuids:
                    # Generate unique filename to avoid caching issues in web app
                    unique_id = uuid.uuid4().hex
                    filename_base = unique_id
                else:
                    filename_base = self.sanitize_filename(title)
                
                filename = os.path.join(output_dir, f"{filename_base}.jpg")
                
                print(f"       Génération de la miniature...")
                saved_path = self.generate_thumbnail(title, filename)
                
                if saved_path:
                    print(f"       Miniature sauvegardée: {saved_path}")
                
                results.append({
                    "title": title,
                    "thumbnail": saved_path
                })
        except AuthenticationError:
            print("\nArrêt du programme dû à une erreur d'authentification.")
            return results
            
        return results

def get_user_input():
    titles = []
    print("Entrez les titres de 10 vidéos (appuyez sur Entrée après chaque titre) :")
    for i in range(1, 11):
        while True:
            title = input(f"Titre {i}: ").strip()
            if title:
                titles.append(title)
                break
            print("Le titre ne peut pas être vide.")
    return titles

if __name__ == "__main__":
    try:
        optimizer = YoutubeOptimizer()
        titles = get_user_input()
        optimizer.process_videos(titles)
        print("\nTraitement terminé !")
    except ValueError as e:
        print(f"Erreur de configuration: {e}")
    except KeyboardInterrupt:
        print("\nOpération annulée par l'utilisateur.")
