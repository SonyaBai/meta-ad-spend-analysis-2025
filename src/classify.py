"""Assign an advertiser category from the page name and the disclaimer.

The Meta report has no category field. The label below is a keyword rule,
applied independently to the disclaimer and to the page name. The higher
priority match wins. "these ads ran without a disclaimer" is ignored and the
page name is used on its own.

Priority, when the two strings disagree: party, candidate or officeholder,
government, media, advocacy, company. A matched label outranks unclassified.

The rules miss candidates who advertise under a personal name only. A
disclaimer shaped "{name} for {state}" is treated as a candidate, which also
catches a few issue names. "Inc." and "LLC" are weak company signals because
nonprofits and issue groups use them; advocacy words are checked first so
"association" and "foundation" are not called companies. Bare "co" is not
used: in this file it also means county or Colorado. Nothing here is a legal
determination of committee type.
"""

from __future__ import annotations

import re

from src.constants import CATEGORY_PRIORITY, NO_DISCLAIMER


def normalize(text: str) -> str:
    value = str(text).casefold().replace("&", " and ")
    value = value.replace("l.l.c", "llc")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = value.replace(" l l c ", " llc ")
    return re.sub(r"\s+", " ", value).strip()


def classify_text(text: str) -> str | None:
    """Return a category for one string, or None when no rule matches."""
    name = normalize(text)
    if not name or name == NO_DISCLAIMER:
        return None

    # "Democrats for …" and "Republicans for …" are usually advocacy names,
    # not the party committee.
    if re.search(r"\b(democrats|republicans|gop)\s+for\b", name):
        return "advocacy"

    if re.search(r"\bgovernors association\b", name):
        return "party"

    party_patterns = (
        r"\bdemocratic party\b",
        r"\brepublican party\b",
        r"\blibertarian party\b",
        r"\bgreen party\b",
        r"\bworking families party\b",
        r"\bforward party\b",
        r"\bconstitution party\b",
        r"\bdemocratic national committee\b",
        r"\brepublican national committee\b",
        r"\bdemocratic congressional campaign committee\b",
        r"\bdemocratic senatorial campaign committee\b",
        r"\bnational republican congressional committee\b",
        r"\bnational republican senatorial committee\b",
        r"\bdemocratic legislative campaign committee\b",
        r"\brepublican state leadership committee\b",
        r"\b(dnc|rnc|dccc|dscc|nrcc|nrsc|dlcc|rslc|dga|rga)\b",
        r"\b(county|state|city|town) (democratic|republican|libertarian|green)\b",
        r"\b(democratic|republican|libertarian|green) (county|state|party) committee\b",
        r"\b(democratic|republican|libertarian|green) committee\b",
        r"\byoung (democrats|republicans)\b",
        r"\bcollege (democrats|republicans)\b",
        r"\b(democratic|republican) national\b",
        r"\bdfl\b",
        r"\bgop\b",
    )
    if any(re.search(pattern, name) for pattern in party_patterns):
        return "party"

    if re.search(r"\bcampaign for\b", name):
        return "advocacy"

    # Campaign language is checked before government so "for governor" and
    # "committee to elect" stay candidates. Bare titles are checked after
    # government so "office of the governor" stays government.
    campaign_patterns = (
        r"\bfor congress\b",
        r"\bfor senate\b",
        r"\bfor state senate\b",
        r"\bfor state house\b",
        r"\bfor state representative\b",
        r"\bfor governor\b",
        r"\bfor president\b",
        r"\bfor mayor\b",
        r"\bfor assembly\b",
        r"\bfor attorney general\b",
        r"\bfor sheriff\b",
        r"\bfor treasurer\b",
        r"\bfor commissioner\b",
        r"\bfor commission\b",
        r"\bfor judge\b",
        r"\bfor district attorney\b",
        r"\bfor county\b",
        r"\bfor city council\b",
        r"\bfor council\b",
        r"\bfor school board\b",
        r"\bfor legislature\b",
        r"\bfor delegate\b",
        r"\bfor representative\b",
        r"\bfor comptroller\b",
        r"\bfor auditor\b",
        r"\bfor supervisor\b",
        r"\bfor alderman\b",
        r"\bfor trustee\b",
        r"\bfor congressman\b",
        r"\bfor congresswoman\b",
        r"\breelect\b",
        r"\bre elect\b",
        r"\bexploratory committee\b",
        r"\bcommittee to elect\b",
        r"\bcampaign committee\b",
    )
    if any(re.search(pattern, name) for pattern in campaign_patterns):
        return "candidate"
    if name.endswith(" campaign") or name.startswith("elect "):
        return "candidate"
    if re.search(r"\bfriends of (?!the\b)", name):
        return "candidate"
    # "{name} for Texas" and the other state names. This is campaign copy in
    # this file. A few issue names use the same shape ("affordable energy for
    # New Jersey"); they are rare next to the candidate spend.
    states = (
        "alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|"
        "florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|"
        "louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|"
        "missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|"
        "new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|"
        "rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|"
        "virginia|washington|west virginia|wisconsin|wyoming|district of columbia|"
        "puerto rico"
    )
    if re.search(rf"\bfor (?:the )?({states})\b", name):
        return "candidate"
    if re.search(r"\bfor(?: [a-z0-9]+){0,4} secretary of state\b", name):
        return "candidate"
    # "Virginians for …", "Americans for …": advocacy names, checked after the
    # office and state campaign phrases so "for Senate" still wins.
    if re.search(
        r"\b(?:americans|citizens|people|women|moms|texans|californians) for\b"
        r"|\b[a-z]+ians for\b",
        name,
    ):
        return "advocacy"

    government_patterns = (
        r"\bcity of\b",
        r"\bcounty of\b",
        r"\btown of\b",
        r"\bvillage of\b",
        r"\bborough of\b",
        r"\btownship of\b",
        r"\bstate of\b",
        r"\bdepartment of\b",
        r"\bdept of\b",
        r"\boffice of\b",
        r"\blocal government\b",
        r"\bgovernment\b",
        r"\bboard of elections\b",
        r"\belection commission\b",
        r"\bschool district\b",
        r"\bpublic schools\b",
        r"\bcommunity college\b",
        r"\bstate university\b",
        r"\bcity council\b",
        r"\bcounty commission\b",
        r"\bnational guard\b",
        r"\bsecretary of state\b",
    )
    if any(re.search(pattern, name) for pattern in government_patterns):
        return "government"

    officeholder_patterns = (
        r"\b(congressman|congresswoman|congressperson)\b",
        r"\b(senator|state senator)\b",
        r"\bstate representative\b",
        r"\bassemblymember\b",
        r"\b(governor|lt governor|lieutenant governor)\b",
        r"\bmayor\b",
        r"\brepresentative\b",
    )
    if any(re.search(pattern, name) for pattern in officeholder_patterns):
        return "candidate"

    media_patterns = (
        r"\bnewspaper\b",
        r"\bnews\b",
        r"\btimes\b",
        r"\bpost\b",
        r"\btribune\b",
        r"\bherald\b",
        r"\bgazette\b",
        r"\bjournal\b",
        r"\bchronicle\b",
        r"\bdispatch\b",
        r"\bradio\b",
        r"\btelevision\b",
        r"\bbroadcasting\b",
        r"\bmedia group\b",
        r"\bpress\b",
        r"\bmedia\b",
        r"\bnewsmax\b",
        r"\bnewsweek\b",
        r"\bpolitico\b",
        r"\baxios\b",
        r"\breuters\b",
        r"\bassociated press\b",
        r"\bnew yorker\b",
        r"\bmagazine\b",
    )
    if any(re.search(pattern, name) for pattern in media_patterns):
        return "media"

    if re.search(r"\bcredit union\b", name):
        return "company"

    advocacy_patterns = (
        r"\bpolitical action committee\b",
        r"\bsuper pac\b",
        r"\bpacs\b",
        r"\bpac\b",
        r"\baction fund\b",
        r"\baction committee\b",
        r"\bcoalition\b",
        r"\balliance\b",
        r"\bfoundation\b",
        r"\binstitute\b",
        r"\bassociation\b",
        r"\bleague\b",
        r"\bunion\b",
        r"\bfederation\b",
        r"\bsociety\b",
        r"\bcouncil\b",
        r"\bvictory fund\b",
        r"\b501 c\b",
        r"\bnonprofit\b",
        r"\bnon profit\b",
        r"\bcitizens for\b",
        r"\bpeople for\b",
        r"\bamericans for\b",
        r"\bwomen for\b",
        r"\bmoms for\b",
        r"\bprojects?\b",
        r"\bwithout borders\b",
        r"\bred cross\b",
        r"\bsalvation army\b",
        r"\bworld food program\b",
        r"\bcentral kitchen\b",
        r"\bplanned parenthood\b",
        r"\baction against\b",
        r"\bmarch\b",
        r"\bfood bank\b",
    )
    if any(re.search(pattern, name) for pattern in advocacy_patterns):
        return "advocacy"

    company_patterns = (
        r"\bllc\b",
        r"\binc\b",
        r"\bincorporated\b",
        r"\bcorp\b",
        r"\bcorporation\b",
        r"\bltd\b",
        r"\blimited\b",
        r"\bcompany\b",
        r"\bplc\b",
        r"\bbank\b",
    )
    if any(re.search(pattern, name) for pattern in company_patterns):
        return "company"
    return None


def classify_pair(page_name: str, disclaimer: str) -> str:
    """Classify one page-id and disclaimer pair from the two name fields."""
    texts = []
    if disclaimer and normalize(disclaimer) != NO_DISCLAIMER:
        texts.append(disclaimer)
    if page_name:
        texts.append(page_name)
    found = [label for text in texts if (label := classify_text(text))]
    if not found:
        return "other"
    for label in CATEGORY_PRIORITY:
        if label in found:
            return label
    return "other"
