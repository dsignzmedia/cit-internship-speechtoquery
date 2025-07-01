from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import speech_recognition as sr
from pydub import AudioSegment
from sql_generator import SQLGenerator
import uuid
import os
import tempfile
import codecs
import datetime
import re
from openai_helper import summarize_db_results  # 👈 import this
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import traceback



def safe_strip(value):
    return str(value).strip().lower() if value is not None else ''

def remove_duplicates_safely(db_results):
    seen_keys = set()
    unique_results = []

    for row in db_results:
        # Use safe_strip on all fields
        name = safe_strip(row[0]) if len(row) > 0 else ''
        location = safe_strip(row[1]) if len(row) > 1 else ''
        url = safe_strip(row[4]) if len(row) > 4 else ''

        key = (name, location, url)

        if key not in seen_keys:
            seen_keys.add(key)
            unique_results.append(row)

    return unique_results




def insert_current_year(text):
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month

    month_to_number = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    week_start_day = {'first': 1, 'second': 8, 'third': 15, 'fourth': 22, 'last': 22}

    # holiday_to_month = {
    #     'Christmas': 'December',
    #     'Thanksgiving': 'November',
    #     'New Year': 'January',
    #     'Easter': 'March'
    # }

    # Pattern: (first|second|...) week (of)? (Christmas|Thanksgiving|...)
    #holiday_week_pattern = r'\b(' + '|'.join(week_start_day.keys()) + r')\s+week(?:\s+of)?\s+(' + '|'.join(holiday_to_month.keys()) + r')\b'

    # def replace_holiday_week(match):
    #     week = match.group(1).lower()
    #     holiday = match.group(2)
    #     month_str = holiday_to_month[holiday]
    #     month_num = month_to_number[month_str]
    #     start = week_start_day[week]
    #     end = start + 6
    #     year = current_year if month_num >= current_month else current_year + 1
    #     return f"{month_str} {start} {year} to {month_str} {end} {year}"

    # text = re.sub(holiday_week_pattern, replace_holiday_week, text, flags=re.IGNORECASE)


    # Handle date ranges like "March 2nd to 4th"
    range_pattern = r'\b(' + '|'.join(month_to_number) + r')\s+(\d{1,2})(st|nd|rd|th)?\s+(to|-)\s+(\d{1,2})(st|nd|rd|th)?\b'
    def add_year_to_range(match):
        month_str = match.group(1)
        start_day = match.group(2)
        end_day = match.group(5)  # Correct group for end day
        month_num = month_to_number[month_str]
        year = current_year if month_num >= current_month else current_year + 1
        # Add month to end date explicitly
        return f"{month_str} {start_day} {year} to {month_str} {end_day} {year}"

    text = re.sub(range_pattern, add_year_to_range, text)

    # Handle phrases like "first week of April"
    week_pattern = r'\b(first|second|third|fourth)\s+week\s+of\s+(' + '|'.join(month_to_number) + r')\b'
    week_start_day = {'first': 1, 'second': 8, 'third': 15, 'fourth': 22}
    def add_year_to_week(match):
        week = match.group(1).lower()
        month_str = match.group(2)
        month_num = month_to_number[month_str]
        start = week_start_day[week]
        end = start + 6
        year = current_year if month_num >= current_month else current_year + 1
        return f"{month_str} {start} {year} to {month_str} {end} {year}"

    text = re.sub(week_pattern, add_year_to_week, text, flags=re.IGNORECASE)

    # Handle single dates like "July 5th"
    single_pattern = r'\b(' + '|'.join(month_to_number) + r')\s+(\d{1,2})(st|nd|rd|th)?\b'
    def add_year_to_single(match):
        month_str = match.group(1)
        day = match.group(2)
        month_num = month_to_number[month_str]
        year = current_year if month_num >= current_month else current_year + 1
        return f"{month_str} {day} {year}"

    text = re.sub(single_pattern, add_year_to_single, text)


    # Handle vague holiday mentions like "Christmas week", "Thanksgiving", etc.
    #vague_holiday_pattern = r'\b(Christmas|Thanksgiving|New Year|Easter)(?:\s+(first|second|third|fourth|last)\s+week|\s+week)?\b(?!\s+\d{4})'

    #def add_year_to_vague_holiday(match):
    #   holiday = match.group(1)
    #    modifier = match.group(2)
    #    if modifier:
        # Compose with modifier + "week" + year at the end
    #         return f"{holiday} {modifier} week {current_year}"
    #     else:
    #         return f"{holiday} {current_year}"
            
    # text = re.sub(vague_holiday_pattern, add_year_to_vague_holiday, text, flags=re.IGNORECASE)
    
    return text

from xampp import run_query  # ✅ Import the query runner from xampp.py

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set ffmpeg path explicitly (update this path if needed)
AudioSegment.converter = r"C:\ffmpeg\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

@app.get("/")
async def root():
    return FileResponse(os.path.join("static","index.html"))

def convert_audio_to_wav(file, target_path):
    audio = AudioSegment.from_file(file)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(target_path, format="wav")

def speech_to_text(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source, duration=5)  # optional limit

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        print("🔇 Could not understand the audio.")
        return "UNRECOGNIZED_AUDIO"
    except sr.RequestError as e:
        print(f"🔌 Google Speech Recognition failed: {e}")
        return f"SPEECH_API_ERROR: {e}"


"""
def clean_html(raw_html):
    # Remove HTML tags using regex
    clean_text = re.sub(r'<.*?>', '', raw_html)
    return clean_text

def print_summary(db_results):
    for record in db_results:
        name = record[0]
        location = record[1]
        description_html = record[2]
        price = record[3]
        url = record[4]

        description = clean_html(description_html)
        price_str = price if price is not None else "N/A"

        summary = f"""
#Hotel Name: {name}
#Location: {location}
#Description: {description}
#Price: ${price_str}
#URL: {url}
#-------------------------
"""
        print(summary)

# Example usage with your db_results list
db_results = [
    ['Westin Los Cabos Resort Villas and Spa', 'Los Cabos', '<p>Experience the ultimate wellness retreat in Los Cabos at The Westin Los Cabos Resort Villas &amp; Spa.</p>', '240', 'https://www.vistana.com/destinations/the-westin-los-cabos-resort-villas-spa'],
    ['Riviera Beach Resort', 'Dana Point', '<p>Riviera Beach Resort offers endless ocean views and relaxing accommodations, creating the perfect destination for your next beach vacation.</p>', '149', 'https://www.diamondresorts.com/destinations/property/Riviera-Beach-Resort'],
    # add more entries here...
]

print_summary(db_results)
"""
@app.post("/voice-to-sql/")
async def voice_to_sql(file: UploadFile = File(...)):
    temp_filename = f"{uuid.uuid4()}.wav"
    try:
        print("📥 Received file:", file.filename)
        await file.seek(0)
        convert_audio_to_wav(file.file, temp_filename)
        print("🎧 Converted to WAV and saved as:", temp_filename)

        # Step 1: Transcribe audio
        text = speech_to_text(temp_filename)
        print("📝 Transcribed text:", text)
        
        processed_text=insert_current_year(text)
        print("PT:          ",processed_text)
        # Step 2: Generate SQL
        generator = SQLGenerator()
        result = generator.generate_query(processed_text)
        print("📄 SQL generation result:", result)

        if result["success"]:
            sql_query = codecs.decode(result["query"], 'unicode_escape')

            # Step 3: Run SQL on MySQL (XAMPP)
            try:
                db_results = run_query(sql_query)
                print("📦 Query Results:", db_results)
                
                db_results_cleaned = remove_duplicates_safely(db_results)
                # After db_results = run_query(sql_query)

                print("✅ Calling summarize_db_results()...")
                summary = summarize_db_results(text, db_results_cleaned)
                print("🧠 Summary generated:", summary)

                return {
                    "success": True,
                    "text": text,
                    "query": sql_query,
                    "results": db_results,
                    "summary": summary  # ✅ Add this
                }

            except Exception as db_error:
                return {
                    "success": False,
                    "text": text,
                    "query": sql_query,
                    "error": f"Database error: {str(db_error)}"
                }

            
        else:
            return {
                "success": False,
                "text": text,
                "error": result["error"]
            }

    except Exception as e:
        traceback_str = traceback.format_exc()
        print("❌ Exception caught in /voice-to-sql/:", traceback_str)
        return JSONResponse(status_code=500, content={"success": False, "error": str(e), "details": traceback_str})

    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)