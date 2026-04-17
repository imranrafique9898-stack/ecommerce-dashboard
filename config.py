"""
config.py — Scraping config with granular product types.
Target: 1000 products per category.
"""

CONFIG = {
    "base_url"      : "https://www.ebay.com/sch/i.html",
    "items_per_page": 60,
    "max_pages"     : 999,          # unlimited — stops when no next page
    "target_per_cat": 1000,         # stop each category at 1000 products
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

# ── WOMENS ────────────────────────────────────────────────────────────────────
# Format: "Category Name" -> (ebay_sacat_id, [search keywords])
SUBCATEGORIES = {

    # ── WOMENS CLOTHING ──────────────────────────────────────────────────────
    "Womens Pants": ("15724", [
        "womens pants", "womens trousers", "womens chinos",
        "womens wide leg pants", "womens cargo pants", "womens dress pants",
        "womens linen pants", "womens jogger pants",
    ]),
    "Womens Jeans": ("15724", [
        "womens jeans", "womens skinny jeans", "womens straight jeans",
        "womens bootcut jeans", "womens wide leg jeans", "womens mom jeans",
        "womens high waist jeans", "womens boyfriend jeans",
    ]),
    "Womens Shirts": ("15724", [
        "womens shirt", "womens button down shirt", "womens blouse",
        "womens oxford shirt", "womens flannel shirt", "womens linen shirt",
        "womens tunic shirt", "womens oversized shirt",
    ]),
    "Womens Tops": ("15724", [
        "womens top", "womens tank top", "womens crop top",
        "womens camisole", "womens sleeveless top", "womens graphic tee",
        "womens polo shirt", "womens tshirt",
    ]),
    "Womens Dresses": ("15724", [
        "womens dress", "womens maxi dress", "womens midi dress",
        "womens mini dress", "womens summer dress", "womens evening dress",
        "womens casual dress", "womens wrap dress",
    ]),
    "Womens Skirts": ("15724", [
        "womens skirt", "womens mini skirt", "womens midi skirt",
        "womens maxi skirt", "womens pleated skirt", "womens denim skirt",
        "womens pencil skirt", "womens floral skirt",
    ]),
    "Womens Jackets & Coats": ("15724", [
        "womens jacket", "womens coat", "womens blazer",
        "womens puffer jacket", "womens leather jacket", "womens trench coat",
        "womens denim jacket", "womens winter coat",
    ]),
    "Womens Sweaters & Hoodies": ("15724", [
        "womens sweater", "womens hoodie", "womens cardigan",
        "womens pullover", "womens sweatshirt", "womens knit sweater",
        "womens zip up hoodie", "womens turtleneck",
    ]),
    "Womens Activewear": ("15724", [
        "womens leggings", "womens yoga pants", "womens sports bra",
        "womens athletic shorts", "womens gym top", "womens running jacket",
        "womens workout set", "womens compression pants",
    ]),

    # ── WOMENS SHOES ─────────────────────────────────────────────────────────
    "Womens Sneakers": ("3034", [
        "womens sneakers", "womens running shoes", "womens athletic shoes",
        "womens canvas sneakers", "womens white sneakers", "womens platform sneakers",
        "womens casual sneakers", "womens walking shoes",
    ]),
    "Womens Heels": ("3034", [
        "womens heels", "womens high heels", "womens stilettos",
        "womens pumps", "womens block heels", "womens kitten heels",
        "womens wedge heels", "womens strappy heels",
    ]),
    "Womens Boots": ("3034", [
        "womens boots", "womens ankle boots", "womens knee high boots",
        "womens chelsea boots", "womens combat boots", "womens winter boots",
        "womens cowboy boots", "womens rain boots",
    ]),
    "Womens Sandals & Flats": ("3034", [
        "womens sandals", "womens flat sandals", "womens flip flops",
        "womens ballet flats", "womens loafers", "womens mules",
        "womens slip on shoes", "womens espadrilles",
    ]),

    # ── WOMENS ACCESSORIES ───────────────────────────────────────────────────
    "Womens Bags & Handbags": ("169291", [
        "womens handbag", "womens tote bag", "womens shoulder bag",
        "womens crossbody bag", "womens clutch bag", "womens backpack",
        "womens satchel", "womens mini bag",
    ]),
    "Womens Jewelry": ("281", [
        "womens necklace", "womens earrings", "womens bracelet",
        "womens ring", "womens gold necklace", "womens silver ring",
        "womens pearl earrings", "womens charm bracelet",
    ]),
    "Womens Watches": ("31387", [
        "womens watch", "womens gold watch", "womens silver watch",
        "womens smartwatch", "womens luxury watch", "womens fashion watch",
        "womens rose gold watch", "womens bracelet watch",
    ]),

    # ── MENS CLOTHING ────────────────────────────────────────────────────────
    "Mens Pants": ("1059", [
        "mens pants", "mens trousers", "mens chinos",
        "mens cargo pants", "mens dress pants", "mens linen pants",
        "mens slim fit pants", "mens jogger pants",
    ]),
    "Mens Jeans": ("1059", [
        "mens jeans", "mens skinny jeans", "mens straight jeans",
        "mens slim jeans", "mens bootcut jeans", "mens relaxed jeans",
        "mens distressed jeans", "mens dark wash jeans",
    ]),
    "Mens Shirts": ("1059", [
        "mens shirt", "mens dress shirt", "mens button down shirt",
        "mens oxford shirt", "mens flannel shirt", "mens linen shirt",
        "mens casual shirt", "mens formal shirt",
    ]),
    "Mens Tshirts & Tops": ("1059", [
        "mens tshirt", "mens graphic tee", "mens polo shirt",
        "mens tank top", "mens henley shirt", "mens long sleeve shirt",
        "mens v neck tshirt", "mens crew neck tshirt",
    ]),
    "Mens Jackets & Coats": ("1059", [
        "mens jacket", "mens coat", "mens blazer",
        "mens puffer jacket", "mens leather jacket", "mens trench coat",
        "mens denim jacket", "mens winter coat",
    ]),
    "Mens Sweaters & Hoodies": ("1059", [
        "mens hoodie", "mens sweater", "mens cardigan",
        "mens pullover", "mens sweatshirt", "mens zip up hoodie",
        "mens crewneck sweatshirt", "mens knit sweater",
    ]),
    "Mens Suits & Formal": ("1059", [
        "mens suit", "mens blazer", "mens dress pants",
        "mens tuxedo", "mens waistcoat", "mens formal shirt",
        "mens suit jacket", "mens slim fit suit",
    ]),
    "Mens Activewear": ("1059", [
        "mens gym shorts", "mens athletic pants", "mens compression shorts",
        "mens running shorts", "mens sports top", "mens gym tshirt",
        "mens workout pants", "mens athletic jacket",
    ]),

    # ── MENS SHOES ───────────────────────────────────────────────────────────
    "Mens Sneakers": ("93427", [
        "mens sneakers", "mens running shoes", "mens athletic shoes",
        "mens canvas sneakers", "mens white sneakers", "mens casual sneakers",
        "mens walking shoes", "mens training shoes",
    ]),
    "Mens Boots": ("93427", [
        "mens boots", "mens ankle boots", "mens chelsea boots",
        "mens combat boots", "mens work boots", "mens winter boots",
        "mens cowboy boots", "mens leather boots",
    ]),
    "Mens Dress Shoes": ("93427", [
        "mens dress shoes", "mens oxford shoes", "mens loafers",
        "mens derby shoes", "mens monk strap shoes", "mens formal shoes",
        "mens leather dress shoes", "mens brogues",
    ]),
    "Mens Sandals": ("93427", [
        "mens sandals", "mens flip flops", "mens slides",
        "mens sport sandals", "mens leather sandals", "mens casual sandals",
    ]),

    # ── KIDS CLOTHING ────────────────────────────────────────────────────────
    "Girls Clothing": ("171146", [
        "girls dress", "girls top", "girls pants", "girls skirt",
        "girls jacket", "girls hoodie", "girls leggings", "girls shirt",
    ]),
    "Boys Clothing": ("171146", [
        "boys shirt", "boys pants", "boys jeans", "boys jacket",
        "boys hoodie", "boys shorts", "boys tshirt", "boys suit",
    ]),
    "Girls Shoes": ("57929", [
        "girls sneakers", "girls boots", "girls sandals",
        "girls school shoes", "girls ballet flats", "girls running shoes",
    ]),
    "Boys Shoes": ("57929", [
        "boys sneakers", "boys boots", "boys sandals",
        "boys school shoes", "boys running shoes", "boys casual shoes",
    ]),

    # ── BABY ─────────────────────────────────────────────────────────────────
    "Baby Girl Clothing": ("260018", [
        "baby girl dress", "baby girl outfit", "baby girl onesie",
        "baby girl romper", "baby girl top", "baby girl pants",
    ]),
    "Baby Boy Clothing": ("260018", [
        "baby boy outfit", "baby boy onesie", "baby boy romper",
        "baby boy shirt", "baby boy pants", "baby boy jacket",
    ]),

    # ── VINTAGE ──────────────────────────────────────────────────────────────
    "Vintage Womens": ("175759", [
        "vintage womens dress", "vintage womens jacket", "vintage womens blouse",
        "vintage womens skirt", "vintage womens coat", "retro womens clothing",
    ]),
    "Vintage Mens": ("175759", [
        "vintage mens jacket", "vintage mens shirt", "vintage mens jeans",
        "vintage mens coat", "vintage mens suit", "retro mens clothing",
    ]),
}

# Custom URLs
CUSTOM_URLS = {}

REQUIRED_FIELDS = ["price", "condition", "seller_name", "image_urls"]
