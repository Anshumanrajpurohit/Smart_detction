from supabase import create_client 

SUPABASE_URL = "https://hwxyuvtfoyzycggbypmo.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh3eHl1dnRmb3l6eWNnZ2J5cG1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mjk5Njk1NiwiZXhwIjoyMDY4NTcyOTU2fQ.wNZitOMcjXGAAMbmOLuS-eRpaKPzsaPM0vZ2FKXpAho"
SUPABASE_BUCKET1 = "android"
SUPABASE_BUCKET2 = "faces"

supabase = create_client(SUPABASE_URL , SUPABASE_KEY)