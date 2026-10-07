import os, requests
from typing import Any, Dict, List, Text
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

CAT_API = "https://api.thecatapi.com/v1"
API_KEY = os.getenv("CAT_API_KEY", "live_s0bWOcMuOYl67JnHowLRxdNyeRrwfXYBl6XIVls7pwK57jFnk7NYL0cAvO0D0lZy")
HEADERS = {"x-api-key": API_KEY} if API_KEY else {}

# Random cat
class ActionGetRandomCat(Action):
    def name(self) -> Text:
        return "action_get_random_cat"

    def run(self, dispatcher, tracker, domain):
        try:
            r = requests.get(f"{CAT_API}/images/search", headers=HEADERS, timeout=5)
            r.raise_for_status()
        except Exception:
            dispatcher.utter_message(text="Could not fetch a cat right now.")
            return []

        data = r.json()
        if not data:
            dispatcher.utter_message(text="The cat service returned no data.")
            return []

        img_data = data[0]
        img_url = img_data.get("url")

        dispatcher.utter_message(
            image=img_url,
        )

        # Store the image id for favourites
        cat_id = img_data.get("id")
        if cat_id:
            return [SlotSet("last_cat_id", cat_id)]
        return []

# Cat by breed
class ActionGetCatByBreed(Action):
    def name(self) -> Text:
        return "action_get_cat_by_breed"

    def run(self, dispatcher, tracker, domain):
        breed_name = tracker.get_slot("cat_breed")
        if not breed_name:
            dispatcher.utter_message(response="utter_no_breed_found")
            return []
        breeds = requests.get(f"{CAT_API}/breeds", headers=HEADERS, timeout=5).json()
        breed = next((b for b in breeds if breed_name.lower() in b["name"].lower()), None)
        if not breed:
            dispatcher.utter_message(response="utter_no_breed_found")
            return []
        r = requests.get(f"{CAT_API}/images/search", params={"breed_ids": breed["id"]}, headers=HEADERS, timeout=5)
        img = r.json()[0]["url"]
        temperament = breed["temperament"]
        weight = breed["weight"]["metric"]
        life = breed["life_span"]
        dispatcher.utter_message(
            text=f"{breed['name']} 🐱\nTemperament: {temperament}\nWeight: {weight} kg\nLife span: {life} years",
            image=img,
        )
        return [SlotSet("last_cat_id", r.json()[0]["id"])]

# Favourites
class ActionAddFavourite(Action):
    def name(self) -> Text:
        return "action_add_favourite"

    def run(self, dispatcher, tracker, domain):
        cat_id = tracker.get_slot("last_cat_id")
        if not cat_id:
            dispatcher.utter_message(text="No cat to favourite yet.")
            return []
        payload = {"image_id": cat_id, "sub_id": "student_demo"}
        r = requests.post(f"{CAT_API}/favourites", json=payload, headers=HEADERS, timeout=5)
        if not r.ok:
            dispatcher.utter_message(text="Could not add to favourites.")
            return []
        dispatcher.utter_message(text="Added this cat to favourites 🐾")
        return []

class ActionListFavourites(Action):
    def name(self) -> Text:
        return "action_list_favourites"

    def run(self, dispatcher, tracker, domain):
        try:
            r = requests.get(f"{CAT_API}/favourites", headers=HEADERS, timeout=5)
            r.raise_for_status()
        except Exception:
            dispatcher.utter_message(text="I could not retrieve your favourite cats.")
            return []

        favourites = r.json()
        if not favourites:
            dispatcher.utter_message(response="utter_favourites_empty")
            return []

        # 1) Build one text summary
        lines = []
        for idx, fav in enumerate(favourites, start=1):
            image = fav.get("image", {}) or {}

            fav_id = fav.get("id")
            lines.append(f"{idx}. favourite id {fav_id}")

        dispatcher.utter_message(
            text="Your favourite cats:\n" + "\n".join(lines)
        )

        # 2) Send the images as separate messages
        # A web front end can group these in a carousel
        for fav in favourites:
            image = fav.get("image", {}) or {}
            url = image.get("url")
            if url:
                dispatcher.utter_message(image=url)

        return []

class ActionRemoveFavourite(Action):
    def name(self) -> Text:
        return "action_remove_favourite"

    def run(self, dispatcher, tracker, domain):
        fav_id = tracker.get_slot("favourite_id")
        if not fav_id:
            dispatcher.utter_message(text="Please give me a valid favourite number.")
            return []
        r = requests.delete(f"{CAT_API}/favourites/{fav_id}", headers=HEADERS, timeout=5)
        if r.ok:
            dispatcher.utter_message(text=f"Removed favourite.")
        else:
            dispatcher.utter_message(text="Could not remove that favourite.")
        return []