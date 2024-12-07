# src/utils/openai_client.py
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_meals(family_preferences):
    prompt = f"""
    Given the following family dietary preferences:
    Restrictions: {', '.join(family_preferences.get('dietary_restrictions', []))}
    Likes: {', '.join(family_preferences.get('common_likes', []))}
    Dislikes: {', '.join(family_preferences.get('common_dislikes', []))}

    Generate a 7-day meal plan (breakfast, lunch, dinner) with recipes and ingredients.
    Include a short description for each meal and assume {family_preferences.get('servings',4)} servings.
    Respond in JSON:
    {{
      "week_start": "<YYYY-MM-DD>",
      "meals": [
        {{
          "day": "Mon",
          "name": "Grilled Chicken with Rice",
          "servings": {family_preferences.get('servings',4)},
          "ingredients": ["chicken", "rice", "spices"],
          "instructions": "Step by step instructions here",
          "description": "A hearty grilled chicken served with fragrant rice"
        }}
      ]
    }}
    """
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=2000,
        temperature=0.7,
    )
    return response.choices[0].text.strip()

def generate_image(meal_name, description):
    prompt = f"Create a realistic photograph of {meal_name}. {description}"
    img_response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="512x512"
    )
    return img_response["data"][0]["url"]

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript
