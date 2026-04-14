"""
config.py — All settings, categories and keywords.
"""

CONFIG = {
    "base_url"      : "https://www.ebay.com/sch/i.html",
    "items_per_page": 60,
    "max_pages"     : 999,
    "delay_min"     : 3.0,
    "delay_max"     : 6.0,
    "item_delay_min": 2.0,
    "item_delay_max": 4.0,
    "output_json"   : "ebay_items_full.json",
    "output_csv"    : "ebay_items_backup.csv",
    "progress_file" : "scraper_progress.json",
    "patch_progress": "patch_progress.json",
    "page_timeout"  : 25,
    "headless"      : True,
}

SUBCATEGORIES = {
    "Womens Clothing": ("15724", [
        "womens dress", "womens jeans", "womens top", "womens jacket", "womens blouse",
        "womens skirt", "womens pants", "womens sweater", "womens coat", "womens hoodie",
        "womens shorts", "womens leggings", "womens cardigan", "womens shirt", "womens suit",
    ]),
    "Mens Clothing": ("1059", [
        "mens shirt", "mens jeans", "mens jacket", "mens suit", "mens hoodie",
        "mens pants", "mens sweater", "mens coat", "mens shorts", "mens polo",
        "mens blazer", "mens vest", "mens joggers", "mens tshirt", "mens chinos",
    ]),
    "Womens Shoes": ("3034", [
        "womens sneakers", "womens heels", "womens boots", "womens sandals", "womens flats",
        "womens loafers", "womens pumps", "womens wedges", "womens mules", "womens slip on",
        "womens ankle boots", "womens running shoes", "womens ballet flats", "womens platforms",
    ]),
    "Mens Shoes": ("93427", [
        "mens sneakers", "mens boots", "mens loafers", "mens dress shoes", "mens sandals",
        "mens running shoes", "mens oxford shoes", "mens slip on", "mens chelsea boots",
        "mens trainers", "mens moccasins", "mens boat shoes",
    ]),
    "Womens Accessories": ("4251", [
        "womens scarf", "womens belt", "womens hat", "womens gloves", "womens sunglasses",
        "womens wallet", "womens hair accessories", "womens headband",
    ]),
    "Mens Accessories": ("4250", [
        "mens belt", "mens wallet", "mens tie", "mens scarf", "mens hat",
        "mens sunglasses", "mens cufflinks",
    ]),
    "Womens Bags & Handbags": ("169291", [
        "womens handbag", "womens tote bag", "womens shoulder bag", "womens clutch",
        "womens crossbody bag", "womens backpack", "womens purse", "womens satchel",
    ]),
    "Kids Clothing": ("171146", [
        "kids dress", "boys jeans", "girls top", "kids jacket", "boys shirt",
        "girls dress", "kids hoodie", "boys shorts", "girls skirt", "kids coat",
    ]),
    "Baby Clothing": ("260018", [
        "baby onesie", "baby dress", "baby romper", "baby jacket", "baby sleepsuit",
        "baby bodysuit", "baby outfit", "newborn clothes",
    ]),
    "Vintage Clothing": ("175759", [
        "vintage dress", "vintage jacket", "vintage jeans", "vintage shirt", "vintage coat",
        "vintage blouse", "vintage skirt", "retro clothing", "vintage sweater",
    ]),
    "Jewelry": ("281", [
        "gold necklace", "silver ring", "diamond earrings", "pearl bracelet", "gold bracelet",
        "silver necklace", "gemstone ring", "gold earrings", "charm bracelet",
    ]),
    "Watches": ("31387", [
        "mens watch", "womens watch", "luxury watch", "automatic watch", "smartwatch",
        "vintage watch", "gold watch", "chronograph watch",
    ]),
}

CUSTOM_URLS = {
    "Johnny Was Tops & Blouses": "https://www.ebay.com/b/Johnny-Was-Tops-Blouses-for-Women/53159/bn_637599",
}

REQUIRED_FIELDS = ["price", "condition", "seller_name", "seller_location", "item_specifics", "image_urls"]
