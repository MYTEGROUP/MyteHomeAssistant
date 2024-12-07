Myte Home Assistant
Myte Home Assistant is an open-source web application designed to help families manage their daily lives more efficiently. The platform integrates tasks, calendars, meal planning, budgeting, and family messaging into a single dashboard. With Myte, families can stay organized and connected.

Features
User Authentication & Family Management:
Register, log in, and manage multiple family members. Invite family members via invite codes.

Tasks & Calendar:
Create tasks, assign them to family members, track due dates, and view family events in a shared calendar.

Meal Planning & Grocery Lists:
Generate weekly meal plans (leveraging OpenAI for suggestions), track dietary preferences, and maintain a family grocery list.

Budgeting:
Add categories, track expenses, and get a snapshot of family spending.

Messaging:
A simple messaging system that allows family members to send messages and keep everyone informed.

Tech Stack
Backend: Python, Flask
Database: MongoDB (via PyMongo)
Authentication & Security: JWT, Passlib for password hashing
AI Features: Integrates with OpenAI API for meal suggestions and image generation
Frontend: Jinja2 templates, Bootstrap for styling, FullCalendar for calendar UI
Others: Dotenv for environment variables, OpenAI Whisper API integration for transcription (if enabled)
Prerequisites
Python 3.9+ (Recommended)
MongoDB Atlas (or a local MongoDB instance)
OpenAI API key (for meal generation and image generation features)
A working SMTP configuration (for email verification and password reset emails)
Installation & Setup
Clone the repository:

bash
Copy code
git clone https://github.com/yourusername/MyteHomeAssistant.git
cd MyteHomeAssistant
Create a virtual environment and install dependencies:

bash
Copy code
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
Set up environment variables:

Copy .env from .env.example (create it if not present) and fill in required details:

bash
Copy code
MONGODB_URI="<your_mongodb_connection_string>"
JWT_SECRET="<your_jwt_secret>"
JWT_ALGORITHM="HS256"
OPENAI_API_KEY="<your_openai_api_key>"
SMTP_PORT=587
SMTP_HOST=smtp.gmail.com
SMTP_USER="<your_smtp_email>"
SMTP_PASS="<your_smtp_password>"
Make sure the .env file is placed in the root directory (MyteHomeAssistant/.env).

Run the application:

bash
Copy code
flask run --host=0.0.0.0 --port=8000
Or run the app.py directly:

bash
Copy code
python app.py
Access the app at http://localhost:8000.

Project Structure
 
bash
Copy code
MyteHomeAssistant/
│
├─ app.py                  # Main Flask application
├─ requirements.txt        # Project dependencies
├─ manifest.json           # PWA manifest
├─ templates/              # Jinja2 HTML templates
├─ static/                 # Static files (CSS, JS, icons)
├─ src/                    # Python source code
│  ├─ auth.py
│  ├─ family.py
│  ├─ tasks.py
│  ├─ calendar.py
│  ├─ budgeting.py
│  ├─ meals.py
│  ├─ messaging.py
│  └─ utils/
│     ├─ db.py             # Database helper
│     ├─ mailer.py         # Email sending utility
│     ├─ openai_client.py  # OpenAI integration
│     ├─ __init__.py
│     └─ ...
├─ uploads/                # Directory for audio uploads, etc.
├─ .env                    # Environment variables file (not committed)
└─ ...
Contributing
We welcome contributions! Please see CONTRIBUTING.md for details on how to propose changes, file issues, and submit pull requests.

License
This project is licensed under the MIT License.

Code of Conduct
Please read our CODE_OF_CONDUCT.md for guidelines on how to engage with the community.

Contact & Community
If you have questions, please open an issue.
Feel free to suggest new features or improvements.
