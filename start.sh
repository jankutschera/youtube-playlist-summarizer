#!/bin/bash

# Start both the web app and the background summarizer

# Start the summarizer in the background
python3 youtube_summarizer.py &

# Start the web app in the foreground (without debug mode to avoid issues)
export FLASK_DEBUG=0
python3 -c "from web_app import app; app.run(host='0.0.0.0', port=5000, debug=False)"
