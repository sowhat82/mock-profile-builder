"""
Name anonymisation: generates culturally appropriate fake names with -test-data suffix.
"""
import random
import re
from faker import Faker

# Curated SG Chinese surnames (romanised)
SG_CHINESE_SURNAMES = [
    "Tan", "Lim", "Lee", "Ng", "Ong", "Wong", "Goh", "Chua", "Chan", "Koh",
    "Teo", "Sim", "Low", "Yeo", "Peh", "Lau", "Soh", "Yap", "Tay", "Wee",
    "Chen", "Lin", "Wang", "Zhang", "Liu", "Yang", "Huang", "Wu", "Zhou",
]

SG_CHINESE_GIVEN_MALE = [
    "Wei", "Ming", "Jian", "Hao", "Jun", "Kai", "Rong", "Xiang", "Yi", "Ze",
    "Boon", "Cheng", "Fong", "Hwee", "Kiat", "Leong", "Soon", "Wah", "Yong",
]

SG_CHINESE_GIVEN_FEMALE = [
    "Li", "Fang", "Hui", "Ling", "Mei", "Na", "Qin", "Ting", "Xin", "Yan",
    "Bee", "Choo", "Geok", "Hwee", "Lay", "Noi", "Siew", "Wati", "Yoke",
]

MALAY_SURNAMES = [
    "bin Abdullah", "binte Ismail", "bin Rahman", "binte Hassan",
    "bin Ahmad", "binte Yusof", "bin Ibrahim", "binte Othman",
]

MALAY_GIVEN_MALE = [
    "Ahmad", "Ali", "Aziz", "Farid", "Hafiz", "Ibrahim", "Ismail", "Jamal",
    "Khairul", "Muhammad", "Nizam", "Omar", "Reza", "Syed", "Zaid",
]

MALAY_GIVEN_FEMALE = [
    "Aishah", "Fatimah", "Hajar", "Hamidah", "Nora", "Nurul", "Rohani",
    "Siti", "Suriani", "Zainab", "Zulaikha",
]

INDIAN_GIVEN_MALE = [
    "Arjun", "Balaji", "Deepak", "Ganesh", "Karthik", "Kumar", "Mohan",
    "Prakash", "Rajesh", "Ravi", "Senthil", "Suresh", "Vijay", "Vikram",
]

INDIAN_GIVEN_FEMALE = [
    "Aishwarya", "Anita", "Divya", "Kavitha", "Lakshmi", "Meena",
    "Priya", "Radha", "Shanti", "Sunita", "Uma",
]

INDIAN_SURNAMES = [
    "Pillai", "Nair", "Krishnan", "Murugan", "Rajan", "Subramaniam",
    "Balakrishnan", "Gopal", "Iyer", "Patel",
]

# Known Chinese surnames for detection
CHINESE_SURNAME_SET = set(s.lower() for s in SG_CHINESE_SURNAMES)

# Common given names for gender detection
WESTERN_MALE_NAMES = {
    "james", "john", "robert", "michael", "william", "david", "richard",
    "joseph", "thomas", "charles", "christopher", "daniel", "paul", "mark",
    "george", "kenneth", "steven", "edward", "brian", "ronald", "peter",
    "andrew", "anthony", "kevin", "jason", "matthew", "gary", "timothy",
    "jose", "larry", "jeffrey", "frank", "scott", "eric", "stephen", "andrew",
    "raymond", "gregory", "joshua", "jerry", "dennis", "walter", "patrick",
    "peter", "harold", "douglas", "henry", "carl", "arthur", "ryan", "roger",
    "joe", "juan", "jack", "albert", "jonathan", "justin", "terry", "gerald",
    "keith", "samuel", "willie", "ralph", "lawrence", "nicholas", "roy",
    "benjamin", "bruce", "brandon", "adam", "harry", "fred", "wayne", "billy",
    "steve", "louis", "jeremy", "aaron", "randy", "eugene", "carlos", "russell",
    "bobby", "victor", "martin", "ernest", "phillip", "todd", "jesse", "craig",
    "alan", "shawn", "clarence", "sean", "philip", "chris", "johnny", "earl",
    "jimmy", "antonio", "danny", "bryan", "tony", "luis", "mike", "stanley",
    "leonard", "nathan", "dale", "manuel", "rodney", "curtis", "norman",
    "allen", "marvin", "vincent", "glen", "jeffery", "travis", "jeff",
    "chad", "jacob", "lee", "melvin", "alfred", "kyle", "francis",
    "bradley", "bernard", "roland", "warren", "alan", "dean", "claude",
    "felix", "ian", "evan", "neil", "ivan", "oscar", "kurt", "joel",
    "ernest", "floyd", "leon", "ray", "lloyd", "don", "max", "rex",
    # SG/Asian male names (English first names used in Singapore)
    "alvin", "calvin", "darren", "desmond", "eldwin", "fabian", "gabriel",
    "irvin", "ivan", "jasper", "kelvin", "lionel", "marcus", "nathaniel",
    "oliver", "percival", "quinton", "reginald", "shaun", "tristan",
    "ulric", "vaughan", "xavier", "yannick", "zachary",
}
WESTERN_FEMALE_NAMES = {
    "mary", "patricia", "jennifer", "linda", "barbara", "elizabeth", "susan",
    "jessica", "sarah", "karen", "lisa", "nancy", "betty", "margaret", "sandra",
    "ashley", "emily", "dorothy", "melissa", "deborah", "stephanie", "helen",
    "sharon", "donna", "carol", "ruth", "virginia", "pamela", "amy", "angela",
    "diane", "anna", "brenda", "janet", "maria", "julie", "victoria", "laura",
    "frances", "alice", "kathleen", "beverly", "denise", "tammy", "irene",
    "jane", "lori", "marilyn", "andrea", "kathryn", "louise", "rose",
    "cynthia", "theresa", "jacqueline", "gloria", "wanda", "evelyn",
    "cheryl", "mildred", "katherine", "joan", "ashley", "judith", "kelly",
    "nicole", "judy", "christina", "kathy", "teresa", "dawn", "doris",
    "rachel", "caroline", "amanda", "tina", "holly", "jessica", "melanie",
    "diana", "robin", "crystal", "wendy", "grace", "brittany", "amber",
    "danielle", "megan", "vanessa", "natalie", "sheila", "ann", "marie",
    "claire", "eleanor", "june", "abigail", "emma", "olivia", "sophia",
    "isabella", "ava", "mia", "ella", "chloe", "madison", "brooklyn",
    # SG/Asian female names (English first names used in Singapore)
    "adeline", "belinda", "corinna", "denise", "elaine", "felicia",
    "germaine", "hwee", "irene", "joanna", "kathleen", "lynnette",
    "marina", "nadine", "ophelia", "pauline", "queenie", "rachelle",
    "serene", "theresa", "ursula", "valerie", "winnie", "yvonne",
}


def _detect_gender(given_name: str) -> str:
    """Heuristic gender detection. Returns 'M', 'F', or 'U' (unknown)."""
    n = given_name.lower()
    if n in WESTERN_MALE_NAMES or n in {g.lower() for g in MALAY_GIVEN_MALE + INDIAN_GIVEN_MALE + SG_CHINESE_GIVEN_MALE}:
        return "M"
    if n in WESTERN_FEMALE_NAMES or n in {g.lower() for g in MALAY_GIVEN_FEMALE + INDIAN_GIVEN_FEMALE + SG_CHINESE_GIVEN_FEMALE}:
        return "F"
    # Heuristic: names ending in 'a' often female (Priya, Kavitha, etc.)
    if n.endswith("a") and len(n) > 3:
        return "F"
    return "U"


def _detect_cultural_style(full_name: str) -> str:
    """Returns 'chinese', 'malay', 'indian', or 'western'."""
    parts = full_name.split()
    if not parts:
        return "western"

    name_lower = full_name.lower()

    # Malay bin/binte/binti pattern
    if re.search(r'\bbin[te]*\b', name_lower):
        return "malay"

    # Check surname against Chinese surname list
    last = parts[-1].lower()
    first = parts[0].lower()
    if last in CHINESE_SURNAME_SET or first in CHINESE_SURNAME_SET:
        return "chinese"

    # Indian surname check
    if last in {s.lower() for s in INDIAN_SURNAMES}:
        return "indian"

    # Indian given name check
    if first in {g.lower() for g in INDIAN_GIVEN_MALE + INDIAN_GIVEN_FEMALE}:
        return "indian"

    return "western"


def generate_fake_name(original_name: str) -> str:
    """Generate a culturally appropriate fake name with -test-data suffix."""
    parts = original_name.strip().split()
    if not parts:
        return "Alex Smith-test-data"

    style = _detect_cultural_style(original_name)
    given = parts[0] if parts else "Alex"
    gender = _detect_gender(given)

    if style == "chinese":
        surname = random.choice(SG_CHINESE_SURNAMES)
        if gender == "F":
            given_name = random.choice(SG_CHINESE_GIVEN_FEMALE)
        else:
            given_name = random.choice(SG_CHINESE_GIVEN_MALE)
        return f"{given_name} {surname}-test-data"

    elif style == "malay":
        if gender == "F":
            given_name = random.choice(MALAY_GIVEN_FEMALE)
            suffix = "binte Abdullah"
        else:
            given_name = random.choice(MALAY_GIVEN_MALE)
            suffix = "bin Abdullah"
        return f"{given_name} {suffix}-test-data"

    elif style == "indian":
        surname = random.choice(INDIAN_SURNAMES)
        if gender == "F":
            given_name = random.choice(INDIAN_GIVEN_FEMALE)
        else:
            given_name = random.choice(INDIAN_GIVEN_MALE)
        return f"{given_name} {surname}-test-data"

    else:
        # Western — use Faker en_GB
        fake = Faker("en_GB")
        if gender == "F":
            fn = fake.first_name_female()
        elif gender == "M":
            fn = fake.first_name_male()
        else:
            fn = fake.first_name()
        ln = fake.last_name()
        return f"{fn} {ln}-test-data"
