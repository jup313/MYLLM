#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5055))
    print(f"\n🚀 Tax AI Social Dashboard starting...")
    print(f"📊 Dashboard: http://localhost:{port}")
    print(f"⏰ Daily generation: {os.getenv('SCHEDULE_HOUR', '6')}:00 AM")
    print(f"Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=port, debug=False)
