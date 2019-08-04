VISION_IMAGE_SIZE_LIMIT = 4000000
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
SAFE_ANN_LIKELIHOODS = ['unknown', 'very unlikely', 'unlikely', 'possible', 'likely', 'very likely']
SAFE_ANN_TYPES = ['adult', 'spoof', 'medical', 'violence', 'racy']
SAFE_ANN_THRESHOLD = 3

# Google Datastore constants
MSG = 'Message'
USERNAME = 'username'
FILE_ID = 'file_id'
FILE_TYPE = 'file_type'
MSG_TEXT = 'message_text'
EXPIRY = 'expiry'
SETTING = 'Setting'
VALUE = 'value'

# Inline keyboard constants
UNDO = 'undo'
DELETE = 'delete'
