import time
import random
from django.core.management.base import BaseCommand
# --- NEW: Import the background task instead of the direct processor ---
from core.tasks import analyze_disaster_intel_task

class Command(BaseCommand):
    help = 'Simulates a live social media feed using Dragonfly Task Queue'

    def handle(self, *args, **options):
        mock_tweets = [
            # --- OFFICIAL SOURCES (Weight: 15.0) ---
            {"user": "ndrfhq", "text": "CRITICAL: NDRF teams deployed in Patna for flood rescue. #BiharFloods"},
            {"user": "uppolice", "text": "Traffic advisory: Storm hitting Lucknow. Stay indoors. #LucknowStorm"},
            
            # --- NEWS SOURCES (Weight: 7.0) ---
            {"user": "ani", "text": "Watch: Massive forest fire in Dehradun hills. #DehradunFire"},
            {"user": "timesofindia", "text": "Lucknow faces severe power outage. #LucknowStorm"},
            
            # --- TRENDING CITIZEN CLUSTER (Triggers 1.5x Multiplier) ---
            {"user": "User_Alpha", "text": "Heavy winds blowing away sheds in Lucknow! #LucknowStorm"},
            {"user": "User_Beta", "text": "Trees falling down near Hazratganj. Stay safe! #LucknowStorm"},
            {"user": "User_Gamma", "text": "Visibility is zero on the highway. #LucknowStorm"},
            {"user": "User_Delta", "text": "Is the roof shaking for anyone else? #LucknowStorm"},
            {"user": "User_Epsilon", "text": "Major rain started in Gomti Nagar. #LucknowStorm"},
            
            # --- GENERAL SOURCES ---
            {"user": "Varanasi_Update", "text": "Ganga water level is definitely higher today. #VaranasiAlert"},
        ]

        self.stdout.write(self.style.SUCCESS('🚀 Starting Production-Ready Mock Feed (Task Queue Active)...'))

        while True:
            tweet = random.choice(mock_tweets)
            post_id = str(random.randint(100000, 999999))
            
            self.stdout.write(f"📥 INGESTING: Post from @{tweet['user']}")
            
            # --- THE MAGICAL HANDOFF ---
            # .delay() sends the data to Dragonfly. It does NOT wait for the result.
            analyze_disaster_intel_task.delay(tweet['text'], tweet['user'], post_id)
            
            self.stdout.write(self.style.NOTICE(f"   ✅ Task queued in Dragonfly for @{tweet['user']}"))
            self.stdout.write("-" * 50)
            
            # Simulating high-speed ingestion (1 second interval)
            time.sleep(1)