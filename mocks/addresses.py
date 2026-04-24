"""
Address anonymisation: generates plausible fake addresses in the same country.
"""
import random
import re

# Singapore street types
SG_STREET_TYPES = [
    "Avenue", "Road", "Street", "Drive", "Lane", "Crescent",
    "Close", "Way", "Boulevard", "Place", "Garden", "Rise",
    "Walk", "View", "Hill", "Heights",
]

SG_STREET_NAMES = [
    "Orchard", "Bukit Timah", "Clementi", "Jurong", "Tampines",
    "Woodlands", "Yishun", "Ang Mo Kio", "Toa Payoh", "Bedok",
    "Pasir Ris", "Punggol", "Sengkang", "Bishan", "Serangoon",
    "Hougang", "Kallang", "Novena", "Newton", "Holland",
    "Buona Vista", "Queenstown", "Redhill", "Tiong Bahru", "Telok Blangah",
]

SG_BUILDING_TYPES = [
    "Tower", "Court", "Place", "Residence", "Gardens", "Park",
    "Suites", "Mansions", "Ville", "Bay",
]

SG_BUILDING_NAMES = [
    "Jade", "Pearl", "Emerald", "Crystal", "Golden", "Silver",
    "Horizon", "Panorama", "Heritage", "Prestige", "Grandeur",
    "Sanctuary", "Pinnacle", "Summit", "Orion", "Aurora",
]

# Valid SG postal district first-2-digit ranges
SG_POSTAL_DISTRICTS = [
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
    "21", "22", "23", "27", "28", "29", "30", "31", "32", "33",
    "34", "35", "36", "37", "38", "39", "40", "41", "42", "43",
    "44", "45", "46", "47", "48", "49", "50", "51", "52", "53",
    "54", "55", "56", "57", "58", "59", "60", "61", "62", "63",
    "64", "65", "66", "67", "68", "69", "70", "71", "72", "73",
    "75", "76", "77", "78", "79", "80", "81", "82",
]


def _generate_sg_postal_code() -> str:
    district = random.choice(SG_POSTAL_DISTRICTS)
    remainder = str(random.randint(0, 9999)).zfill(4)
    return district + remainder


def _generate_sg_address() -> str:
    """Generate a plausible fake Singapore address."""
    # Decide between HDB-style and condo-style
    is_condo = random.random() > 0.4

    block_num = str(random.randint(1, 999))
    street_name = random.choice(SG_STREET_NAMES)
    street_type = random.choice(SG_STREET_TYPES)
    floor = str(random.randint(1, 40)).zfill(2)
    unit = str(random.randint(1, 20)).zfill(2)
    postal = _generate_sg_postal_code()

    if is_condo:
        bld_name = random.choice(SG_BUILDING_NAMES) + " " + random.choice(SG_BUILDING_TYPES)
        return f"{block_num} {street_name} {street_type}, {bld_name}, #{floor}-{unit}, Singapore {postal}"
    else:
        return f"Block {block_num} {street_name} {street_type}, #{floor}-{unit}, Singapore {postal}"


def _detect_country(address: str) -> str:
    """Detect country from address string."""
    addr_lower = address.lower()
    if "singapore" in addr_lower or re.search(r'\b\d{6}\b', addr_lower):
        return "SG"
    if "malaysia" in addr_lower or "kuala lumpur" in addr_lower or "kl" in addr_lower:
        return "MY"
    if "united kingdom" in addr_lower or "england" in addr_lower or "london" in addr_lower:
        return "GB"
    if "united states" in addr_lower or "usa" in addr_lower:
        return "US"
    return "SG"  # Default to Singapore for this use case


def generate_fake_address(original_address: str) -> str:
    """Generate a fake address in the same country as the original."""
    country = _detect_country(original_address)

    if country == "SG":
        return _generate_sg_address()

    elif country == "MY":
        streets = ["Jalan Ampang", "Jalan Bukit Bintang", "Jalan Imbi", "Jalan Pudu", "Lorong Haji Hussein"]
        areas = ["Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Subang Jaya", "Bangsar"]
        num = random.randint(1, 100)
        postcode = str(random.randint(10000, 99999))
        return f"{num} {random.choice(streets)}, {random.choice(areas)}, {postcode}, Malaysia"

    elif country == "GB":
        from faker import Faker
        fake = Faker("en_GB")
        return fake.address().replace("\n", ", ")

    else:
        from faker import Faker
        fake = Faker("en_US")
        return fake.address().replace("\n", ", ")
