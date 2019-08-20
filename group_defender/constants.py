MSG_LIFETIME = 1  # 1 day
TIMEOUT = 20

# Payment constants
PAYMENT = 'payment'
PAYMENT_PAYLOAD = 'payment_payload'
PAYMENT_CURRENCY = 'USD'
PAYMENT_PARA = 'payment_para'
PAYMENT_THANKS = 'Say Thanks 😁 ($1)'
PAYMENT_COFFEE = 'Coffee ☕ ($3)'
PAYMENT_BEER = 'Beer 🍺 ($5)'
PAYMENT_MEAL = 'Meal 🍲 ($10)'
PAYMENT_CUSTOM = 'Say Awesome 🤩 (Custom)'
PAYMENT_DICT = {PAYMENT_THANKS: 1, PAYMENT_COFFEE: 3, PAYMENT_BEER: 5, PAYMENT_MEAL: 10}
WAIT_PAYMENT = 0

# File types
AUDIO = 'audio'
DOCUMENT = 'document'
PHOTO = 'photo'
VIDEO = 'video'
URL = 'url'

# Attachment Scanner constants
OK = 'ok'
FOUND = 'found'
WARNING = 'warning'
PENDING = 'pending'
FAILED = 'failed'

# Google Vision constants
GCP_LIKELIHOODS = ['unknown', 'very unlikely', 'unlikely', 'possible', 'likely', 'very likely']
GCP_THRESHOLD = 3
GCP_LIMIT = 950

# Azure Content Moderator constants
AZURE_LIMIT = 4950
AZURE_THRESHOLD = 0.5

# Google Datastore constants
MSG = 'Message'
USERNAME = 'username'
FILE_ID = 'file_id'
FILE_TYPE = 'file_type'
MSG_TEXT = 'message_text'
EXPIRY = 'expiry'
SETTING = 'Setting'
VALUE = 'value'
API_COUNT = 'API_Count'
NAME = 'name'
YEAR = 'year'
MONTH = 'month'
COUNT = 'count'
GCP = 'gcp'
AZURE = 'azure'
BOT_COUNT = 'Bot_Count'
FILE = 'file'

# Inline keyboard constants
UNDO = 'undo'
DELETE = 'delete'
