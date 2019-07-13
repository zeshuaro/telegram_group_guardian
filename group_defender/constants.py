FILE_TYPE_NAMES = {"aud": "audio", "doc": "document", "img": "image", "vid": "video", "url": "url"}
VISION_IMAGE_SIZE_LIMIT = 4000000
SAFE_ANN_THRESHOLD = 3
MSG_LIFETIME = 1  # 1 day
TIMEOUT = 20

# Payment Constants
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
