import os
import requests
import base64
import io
import uuid
import re
from openai import OpenAI, AuthenticationError
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv()

class YoutubeOptimizer:
    def __init__(self, api_key=None):
        # Prefer TOGETHER_API_KEY, fallback to OPENAI_API_KEY if needed (though we want to use Together now)
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Aucune clé API trouvée. Veuillez définir TOGETHER_API_KEY ou OPENAI_API_KEY.")
        
        # Determine which provider to use based on available key
        self.provider = "together" if os.getenv("TOGETHER_API_KEY") else "openai"

        if self.provider == "together":
            # Initialize OpenAI client but pointing to Together AI base URL
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.together.xyz/v1"
            )
        else:
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

    def add_text_overlay(self, image, title):
        """
        Adds the title as a text overlay on the image.
        Uses a bold font, white text with black outline, centered.
        """
        draw = ImageDraw.Draw(image)
        width, height = image.size

        # Try to load a nice font, fallback to default
        font_size = int(height * 0.15) # Start with 15% of image height
        try:
            # Try some common bold fonts
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if not os.path.exists(font_path):
                 font_path = "arialbd.ttf" # Windows fallback?

            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print("       Police non trouvée, utilisation de la police par défaut.")
            font = ImageFont.load_default()

        # Wrap text logic
        lines = []
        words = title.split()
        current_line = []

        # Safety for very long words or titles
        margin = int(width * 0.05)
        max_width = width - (2 * margin)

        # Helper to check text width
        def get_text_width(text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0]

        # Iteratively reduce font size if a single word is too big
        while font_size > 20:
             # Check if longest word fits
             longest_word = max(words, key=len) if words else ""
             if get_text_width(longest_word, font) < max_width:
                 break
             font_size -= 5
             try:
                 font = ImageFont.truetype(font_path, font_size)
             except:
                 pass

        # Wrap words
        for word in words:
            test_line = ' '.join(current_line + [word])
            w = get_text_width(test_line, font)
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is wider than line, just append it (we shrank font earlier as best as possible)
                    lines.append(word)
        if current_line:
            lines.append(' '.join(current_line))

        # If too many lines, shrink font and retry (simple recursive retry or just shrink)
        # For now, let's just calculate height and center it.

        line_height = bbox = draw.textbbox((0, 0), "Aj", font=font)[3] - draw.textbbox((0, 0), "Aj", font=font)[1]
        line_height = line_height * 1.2 # Add spacing

        total_text_height = len(lines) * line_height

        start_y = (height - total_text_height) // 2

        # Draw text with outline
        outline_width = max(2, int(font_size / 15))

        for i, line in enumerate(lines):
            line_w = get_text_width(line, font)
            x = (width - line_w) // 2
            y = start_y + (i * line_height)

            # Draw outline
            draw.text((x-outline_width, y-outline_width), line, font=font, fill="black")
            draw.text((x+outline_width, y-outline_width), line, font=font, fill="black")
            draw.text((x-outline_width, y+outline_width), line, font=font, fill="black")
            draw.text((x+outline_width, y+outline_width), line, font=font, fill="black")
            # Draw extra diagonal outline for thickness
            draw.text((x-outline_width, y), line, font=font, fill="black")
            draw.text((x+outline_width, y), line, font=font, fill="black")
            draw.text((x, y-outline_width), line, font=font, fill="black")
            draw.text((x, y+outline_width), line, font=font, fill="black")

            # Draw main text
            draw.text((x, y), line, font=font, fill="white")

        return image

    def process_and_compress_image(self, img_content, output_path, title=None, max_size_mb=2.0):
        """
        Crops the image to 16:9 aspect ratio, adds title overlay if provided, and compresses.
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

            # Add text overlay if title is provided
            if title:
                print(f"       Ajout du titre sur l'image...")
                image = self.add_text_overlay(image, title)

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
        Génère une miniature pour la vidéo via l'API (Together AI ou OpenAI) et la sauvegarde localement.
        """
        try:
            # We add "catchy" keywords to the prompt since the user requested catchy thumbnails
            prompt = f"A high quality, catchy YouTube thumbnail for a video titled '{title}'. Bright colors, high contrast, 16:9 aspect ratio. No text."
            
            model = "gpt-image-1.5"
            size = "1536x1024"

            if self.provider == "together":
                model = "black-forest-labs/FLUX.1-schnell"
                # Flux supports standard sizes, usually 1024x1024 or similar, but let's try to request landscape if possible
                # or just standard 1024x1024 and crop. Together AI image gen usually takes width/height in body if not standard OpenAI format,
                # but using the OpenAI client wrapper usually forces standard params.
                # Flux via Together often maps 'size' to width/height.
                # Let's use 1024x768 or similar if supported, otherwise 1024x1024.
                # OpenAI client enforces 'size' enum often.
                # If using OpenAI client with Together, we might need to be careful with 'size' param.
                # '1024x1024' is safest.
                size = "1024x1024"

            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                # quality="high", # Flux via Together might not support 'quality' param
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
            return self.process_and_compress_image(img_content, output_path, title=title)
            
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
