from flask import Flask, render_template, jsonify, Response, request
import azure.cognitiveservices.speech as speechsdk
import os
from dotenv import load_dotenv
import queue
import threading
import json
from datetime import datetime  # Import for date-based file naming

load_dotenv()

app = Flask(__name__)

# Global queue for storing translations
translation_queue = queue.Queue()
is_translating = False

# File path for storing translations
today_date = datetime.now().strftime('%Y-%m-%d')  # Format: YYYY-MM-DD
translation_file_path = f"{today_date}_translations.txt"

class SpeechTranslator:
    def __init__(self):
        self.speech_config = None
        self.translation_recognizer = None
        self.is_translating = False

    def configure_translator(self, input_language, output_language):
        self.speech_config = speechsdk.translation.SpeechTranslationConfig(
            subscription=os.getenv('SPEECH_KEY'),
            region=os.getenv('SPEECH_REGION')
        )
        self.speech_config.speech_recognition_language = input_language
        self.speech_config.add_target_language(output_language)

    def start_translation(self):
        if not self.speech_config:
            raise ValueError("Speech config not set. Call configure_translator first.")

        self.is_translating = True
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.translation_recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=self.speech_config,
            audio_config=audio_config
        )

        def handle_partial_translation(evt):
            if evt.result.reason == speechsdk.ResultReason.TranslatingSpeech:
                output_language = list(self.speech_config.target_languages)[0]
                translation = evt.result.translations[output_language]
                translation_queue.put({'type': 'partial', 'translation': translation})
                self.save_to_file(f"Partial: {translation}\n")

        def handle_final_translation(evt):
            if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
                output_language = list(self.speech_config.target_languages)[0]
                translation = evt.result.translations[output_language]
                translation_queue.put({'type': 'final', 'translation': translation})
                self.save_to_file(f"Final: {translation}\n")

        self.translation_recognizer.recognizing.connect(handle_partial_translation)
        self.translation_recognizer.recognized.connect(handle_final_translation)
        self.translation_recognizer.start_continuous_recognition()

    def stop_translation(self):
        if self.translation_recognizer:
            self.is_translating = False
            self.translation_recognizer.stop_continuous_recognition()

    @staticmethod
    def save_to_file(text):
        """Save translations to the file."""
        with open(translation_file_path, 'a', encoding='utf-8') as file:
            file.write(text)

translator = SpeechTranslator()

@app.route('/')
def home():
    return render_template('indexmast1.html')

@app.route('/start_translation', methods=['POST'])
def start_translation():
    global is_translating
    is_translating = True

    data = request.get_json()
    input_language = data.get('input_language', 'en-US')  # Default to English
    output_language = data.get('output_language', 'en')  # Default to English

    translator.configure_translator(input_language, output_language)
    translator.start_translation()

    return jsonify({'status': 'started'})

@app.route('/stop_translation', methods=['POST'])
def stop_translation():
    global is_translating
    is_translating = False
    translator.stop_translation()
    return jsonify({'status': 'stopped'})

@app.route('/stream')
def stream():
    def generate():
        while True:
            try:
                if not is_translating:
                    break
                # Try to get a translation from the queue with a timeout
                translation_data = translation_queue.get(timeout=0.1)
                yield f"data: {json.dumps(translation_data)}\n\n"
            except queue.Empty:
                continue
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Ensure the file is created at the start
    open(translation_file_path, 'w', encoding='utf-8').close()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
