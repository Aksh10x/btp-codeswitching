"""
Lexicons for the Bengali-Hindi Morphology-Aware Analyzer.

Hindi noun genders, Bengali word dictionary, verb inflection patterns,
and English word list — all in Roman transliteration.
"""

# Hindi feminine nouns (from corpus + common household/everyday items)
# These are nouns whose grammatical gender is feminine in Hindi.
# When a masculine verb appears with one of these, it's a gender error.
HINDI_FEMININE_NOUNS = {
    # From our corpus (study reference nouns)
    "kursi", "khursi",     # chair
    "kitaab", "kitab",     # book
    "roti",                # bread
    "gaadi", "gadi",       # vehicle
    "chaabi", "chabi",     # key
    "khidki", "khidkee",   # window
    "kamar",               # waist/back

    # Common feminine nouns (household/everyday)
    "mez", "table",        # table (mez is F in Hindi)
    "almari", "almaari",   # cupboard
    "botal", "bottle",     # bottle
    "chai",                # tea
    "topi",                # cap
    "chaadar", "chadar",   # sheet/bedsheet
    "thali", "thaali",     # plate
    "sabzi", "sabji",      # vegetable
    "nadi", "nadi",        # river
    "sadak", "sarak",      # road
    "deewar", "diwar",     # wall
    "chhat",               # roof
    "baarish", "barish",   # rain
    "garmi",               # heat
    "sardi",               # cold
    "raat",                # night
    "subah",               # morning
    "dukaan", "dukan",     # shop
    "jeb",                 # pocket
    "ungali", "ungli",     # finger
    "aankh", "ankh",       # eye
    "naak", "nak",         # nose
    "zubaan", "zuban",     # tongue
    "hawa",                # air/wind
    "bijli", "bijali",     # electricity
    "chitthi", "chithi",   # letter
    "mitti", "mati",       # soil/earth
    "dhoop", "dhup",       # sunshine
    "batti",               # light/lamp
    "gali",                # lane/alley
    "chingari",            # spark
    "ladki",               # girl
    "aurat",               # woman
    "behen", "bahen",      # sister
    "maa", "ma",           # mother
    "beti",                # daughter
    "bhabhi",              # sister-in-law
    "didi",                # elder sister
    "mausi",               # maternal aunt
    "nani",                # maternal grandmother
    "dadi",                # paternal grandmother
    "bahu",                # daughter-in-law
    "ladies",              # ladies (used as F in Hindi)
    "class",               # class (F in Hindi)
    "duty",                # duty (F in colloquial Hindi)
    "study",               # study (F in colloquial Hindi)
    "plate",               # plate
    "degree",              # degree
}

# Hindi masculine nouns (for reference — model should NOT flag masc verb with these)
HINDI_MASCULINE_NOUNS = {
    # Study reference nouns
    "darwaza", "darwaaza", "door",  # door
    "pankha", "pankhi",    # fan
    "ghar",                # house
    "paani", "pani",       # water
    "khana", "khaana",     # food
    "haath", "hath",       # hand

    # Common masculine nouns
    "kamra", "kamara",     # room
    "kapda", "kapada",     # cloth
    "ped", "pedh",         # tree
    "paisa", "paise",      # money
    "kaam",                # work
    "aadmi", "admi",       # man
    "ladka",               # boy
    "beta",                # son
    "bhai",                # brother
    "baap",                # father
    "chawal",              # rice
    "dudh", "doodh",       # milk
    "garam",               # hot (adj)
    "phone",               # phone
    "time",                # time
    "school",              # school (M in Hindi)
    "hospital",            # hospital
    "campus",              # campus
}

# Bengali words that appear in Hindi matrix speech
# Maps Bengali word -> {hindi_equiv, meaning, domain}
BENGALI_WORDS = {
    "dorja": {"hindi": "darwaza", "meaning": "door", "domain": "household"},
    "janala": {"hindi": "khidki", "meaning": "window", "domain": "household"},
    "jol": {"hindi": "paani", "meaning": "water", "domain": "household"},
    "bhat": {"hindi": "chawal", "meaning": "rice", "domain": "food"},
    "pakha": {"hindi": "pankha", "meaning": "fan", "domain": "household"},
    "boi": {"hindi": "kitaab", "meaning": "book", "domain": "household"},
    "ghor": {"hindi": "ghar", "meaning": "house", "domain": "household"},
    "kedara": {"hindi": "kursi", "meaning": "chair", "domain": "furniture"},
    "parota": {"hindi": "paratha", "meaning": "paratha/flatbread", "domain": "food"},
    "khabaar": {"hindi": "khana", "meaning": "food", "domain": "food"},
    "hather": {"hindi": "haath", "meaning": "hand", "domain": "body"},
    "panja": {"hindi": "panja", "meaning": "palm/paw", "domain": "body"},
    "badro": {"hindi": "bada/buzurg", "meaning": "elder/big", "domain": "adjective"},
    "mahila": {"hindi": "aurat", "meaning": "woman", "domain": "person"},
    "cheleti": {"hindi": "ladki", "meaning": "girl", "domain": "person"},
    "ami": {"hindi": "mai/mein", "meaning": "I", "domain": "pronoun"},
    "tor": {"hindi": "tera", "meaning": "your", "domain": "pronoun"},
    "bangali": {"hindi": "bengali", "meaning": "Bengali", "domain": "identity"},
    "eta": {"hindi": "yeh/idhar", "meaning": "this/here", "domain": "deictic"},
    "ta": {"hindi": "ek (classifier)", "meaning": "one (classifier)", "domain": "classifier"},

    # Bengali verb forms that appear in code-switched speech
    "khacchi": {"hindi": "kha rahi hai", "meaning": "is eating (F)", "domain": "verb"},
    "korche": {"hindi": "kar rahi hai", "meaning": "is doing", "domain": "verb"},
    "porachuna": {"hindi": "padhai", "meaning": "study/studies", "domain": "noun"},
    "dhalche": {"hindi": "daal raha hai", "meaning": "is pouring", "domain": "verb"},
    "rekh": {"hindi": "rakh", "meaning": "keep/put", "domain": "verb"},
    "bhenge": {"hindi": "toot", "meaning": "broken", "domain": "verb"},
    "gache": {"hindi": "gaya hai", "meaning": "has gone/happened", "domain": "verb"},
    "khola": {"hindi": "khula", "meaning": "open", "domain": "adjective"},
    "jolmo": {"hindi": "janam", "meaning": "birth", "domain": "noun"},
    "khorgoporei": {"hindi": "kharagpur mein", "meaning": "in Kharagpur", "domain": "place"},
    "bagan": {"hindi": "bagicha", "meaning": "garden", "domain": "household"},
    "bagarna": {"hindi": "saaf karna", "meaning": "to clean/tend", "domain": "verb"},
    "ulto": {"hindi": "ulta", "meaning": "upside down", "domain": "adjective"},
    "kore": {"hindi": "karke", "meaning": "having done", "domain": "verb"},
    "chi": {"hindi": "hai (perf. aux.)", "meaning": "has (done)", "domain": "verb"},
    "ache": {"hindi": "hai", "meaning": "is/are", "domain": "verb"},
    "che": {"hindi": "hai (progressive)", "meaning": "is (doing)", "domain": "verb"},

    # Additional Bengali words from corpus
    "aar": {"hindi": "aur", "meaning": "and/more", "domain": "conjunction"},
    "ghum": {"hindi": "neend", "meaning": "sleep", "domain": "noun"},
    "uthlam": {"hindi": "utha (1sg past)", "meaning": "I woke up", "domain": "verb"},
    "pollam": {"hindi": "pati (colloquial)", "meaning": "husband (colloquial)", "domain": "kinship"},
    "tarpore": {"hindi": "uske baad", "meaning": "then/after that", "domain": "conjunction"},
    "banalam": {"hindi": "banaya (1sg)", "meaning": "I made", "domain": "verb"},
    "amar": {"hindi": "mera", "meaning": "my", "domain": "pronoun"},
    "janmo": {"hindi": "janam", "meaning": "birth", "domain": "noun"},
    "hoiche": {"hindi": "hua hai", "meaning": "has happened", "domain": "verb"},
    "beshirbhag": {"hindi": "zyada tar", "meaning": "mostly", "domain": "adverb"},
    "bangla": {"hindi": "bengali", "meaning": "Bengali (language)", "domain": "identity"},
    "kori": {"hindi": "karta/karti hu", "meaning": "I do", "domain": "verb"},
    "chilo": {"hindi": "tha/thi", "meaning": "was", "domain": "verb"},
    "oita": {"hindi": "woh", "meaning": "that", "domain": "pronoun"},
    "thik": {"hindi": "theek", "meaning": "correct/properly", "domain": "adjective"},
    "boiti": {"hindi": "kitaab (def.)", "meaning": "the book (definite)", "domain": "noun"},
    "rekhechi": {"hindi": "rakh diya hai", "meaning": "have kept", "domain": "verb"},
    "geche": {"hindi": "gaya hai", "meaning": "has gone", "domain": "verb"},
    "khule": {"hindi": "khula hua", "meaning": "open (state)", "domain": "adjective"},
    "glasser": {"hindi": "glass ka", "meaning": "of the glass (genitive)", "domain": "noun"},
    "baari": {"hindi": "ghar", "meaning": "house/home", "domain": "household"},
    "rakhe": {"hindi": "rakha hua", "meaning": "kept", "domain": "verb"},
    "bhora": {"hindi": "bhara hua", "meaning": "filled", "domain": "adjective"},
    "jonmo": {"hindi": "janam", "meaning": "birth", "domain": "noun"},
    "paisi": {"hindi": "paise", "meaning": "money (dialectal)", "domain": "noun"},
}

# Bengali morphological markers (suffixes/particles that indicate Bengali)
BENGALI_MARKERS = {
    # Progressive: -che, -chi, -cche, -cchi
    "che", "chi", "cche", "cchi",
    # Perfective: -eche, -echi, -lo, -lam, -le
    "eche", "echi",
    # Copula/auxiliary
    "ache", "achi",
    # Classifier
    "ta", "ti", "khana",
    # Case markers
    "ke", "te", "er", "r",
}

# Verb patterns for gender detection (Roman transliteration)
# Masculine perfective endings
MASCULINE_VERB_PATTERNS = {
    # Perfective: gaya, kiya, liya, diya, hua, aaya, khaya
    "gaya", "kiya", "liya", "diya", "hua", "aaya", "khaya",
    "piya", "soya", "roya", "bola", "chala", "gira", "pada",
    "baitha", "utha", "mara", "toda", "phoda", "tuta", "toota",
    "toot gaya", "ho gaya", "a gaya", "aa gaya", "chala gaya",
    "gir gaya", "tut gaya", "ghus gaya", "ulat gaya", "ulta ho gaya",
    "kharab ho gaya", "kharaab ho gaya",
    # Habitual: -ta
    "karta", "bolta", "padhta", "banata", "sunta", "dekhta",
    "khelta", "sota", "rota", "hota", "jata", "ata", "aata",
    "likhta", "seekhta", "karta tha", "bolta tha", "padhta tha",
    # Progressive: raha
    "raha", "raha hai", "raha tha",
    "kar raha", "bol raha", "padh raha", "bana raha",
    "sun raha", "dekh raha", "khel raha", "so raha",
    "kha raha", "pi raha", "seekh raha", "khol raha",
    "dal raha", "khul raha",
}

# Feminine equivalents of the same verb patterns
FEMININE_VERB_PATTERNS = {
    # Perfective
    "gayi", "ki", "li", "di", "hui", "aayi", "khayi",
    "piyi", "soyi", "royi", "boli", "chali", "giri", "padi",
    "baithi", "uthi", "mari", "todi", "phodi", "tuti", "tooti",
    "toot gayi", "ho gayi", "a gayi", "aa gayi", "chali gayi",
    "gir gayi", "tut gayi", "ghus gayi", "ulat gayi", "ulti ho gayi",
    "kharab ho gayi", "kharaab ho gayi",
    # Habitual: -ti
    "karti", "bolti", "padhti", "banati", "sunti", "dekhti",
    "khelti", "soti", "roti", "hoti", "jati", "ati", "aati",
    "likhti", "seekhti", "karti thi", "bolti thi", "padhti thi",
    # Progressive: rahi
    "rahi", "rahi hai", "rahi thi",
    "kar rahi", "bol rahi", "padh rahi", "bana rahi",
    "sun rahi", "dekh rahi", "khel rahi", "so rahi",
    "kha rahi", "pi rahi", "seekh rahi", "khol rahi",
    "dal rahi", "khul rahi",
}

# Past tense auxiliary (for detecting perfective contexts where "ne" should appear)
PERFECTIVE_MARKERS = {
    "kiya", "ki", "liya", "li", "diya", "di", "khaya", "khayi",
    "piya", "piyi", "bola", "boli", "suna", "suni", "dekha", "dekhi",
    "likha", "likhi", "padha", "padhi", "banaya", "banayi",
    "seekha", "seekhi", "khola", "kholi", "toda", "todi",
}

# Transitive verbs (that require ergative "ne" in perfective)
TRANSITIVE_VERBS_STEMS = {
    "kha", "pi", "bol", "sun", "dekh", "likh", "padh", "bana",
    "seekh", "khol", "tod", "de", "le", "kar", "maar", "dho",
    "bhej", "rakh", "dal", "gir",  # giirana is transitive
}

# English words commonly used in Hindi speech (for language ID)
ENGLISH_COMMON = {
    "the", "a", "an", "is", "are", "was", "were", "i", "you", "he",
    "she", "it", "we", "they", "my", "your", "his", "her", "its",
    "our", "their", "this", "that", "these", "those", "and", "or",
    "but", "if", "then", "so", "because", "yes", "no", "not", "very",
    "ok", "okay", "please", "thank", "thanks", "sorry", "hello", "hi",
    "bye", "good", "bad", "big", "small", "new", "old", "first", "last",
    "here", "there", "now", "then", "today", "tomorrow", "yesterday",
    "also", "only", "just", "still", "already", "about", "after", "before",
    # Education/work terms common in Indian English
    "school", "college", "university", "class", "study", "student",
    "teacher", "sir", "madam", "maam", "english", "hindi", "bengali",
    "medium", "exam", "test", "pass", "fail", "result",
    "hospital", "doctor", "nurse", "patient", "medicine",
    "phone", "mobile", "computer", "laptop", "internet", "online",
    "office", "job", "work", "duty", "salary", "leave",
    "train", "bus", "auto", "taxi", "car", "bike",
    "photo", "video", "camera", "picture", "image",
    "morning", "evening", "night", "afternoon",
    "problem", "issue", "question", "answer",
    "time", "year", "month", "day", "week", "hour", "minute",
    "number", "name", "age", "address",
    "market", "shop", "mall", "store",
    "food", "water", "tea", "coffee", "lunch", "dinner", "breakfast",
    "room", "kitchen", "bathroom", "bedroom",
    "husband", "wife", "family", "son", "daughter", "child", "children",
    "friend", "brother", "sister", "father", "mother",
    "happy", "sad", "angry", "tired", "fine",
    "open", "close", "start", "stop", "come", "go",
    "course", "degree", "physiotherapy", "engineering", "science",
    "explain", "describe", "tell", "speak", "talk", "read", "write",
    "background", "interview", "recording", "research",
    "campus", "hostel", "canteen", "mess", "hall",
    "accident", "actually", "basically", "something", "anything",
    "everything", "nothing", "someone", "everyone",
    "thankyou", "welcome",
    # Additional from corpus
    "chair", "fan", "door", "book", "house", "window", "glass",
    "plate", "key", "keys", "car", "pizza",
    "hand", "hands", "finger", "fingers",
    "service", "repairing", "puncture", "operation",
    "shift", "allotment", "handover", "security",
    "same", "normal", "busy", "easy", "important",
    "explain", "prefer", "attend", "complete",
    "non-veg", "veg", "lunch", "dinner", "breakfast",
    "incident", "situation", "pressure", "load",
    "boys", "girls", "ladies",
    "nice", "fine", "ok", "okay",
    "inter", "graduate", "graduation", "hs",
    "medium", "subject", "language",
    "role", "purpose", "complaint",
    "garden", "marketing", "routine",
}
