import phonenumbers
from phonenumbers import carrier, geocoder, timezone, NumberParseException

_TYPES = {
    phonenumbers.PhoneNumberType.MOBILE: "Mobile",
    phonenumbers.PhoneNumberType.FIXED_LINE: "Fixed line",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed line or mobile",
    phonenumbers.PhoneNumberType.TOLL_FREE: "Toll free",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "Premium rate",
    phonenumbers.PhoneNumberType.VOIP: "VoIP",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "Personal number",
    phonenumbers.PhoneNumberType.PAGER: "Pager",
    phonenumbers.PhoneNumberType.UAN: "UAN",
    phonenumbers.PhoneNumberType.VOICEMAIL: "Voicemail",
    phonenumbers.PhoneNumberType.UNKNOWN: "Unknown",
}


def search(number, region=None):
    number = (number or "").strip()
    if not number:
        return {"ok": False, "error": "Enter a phone number."}
    try:
        parsed = phonenumbers.parse(number, region or None)
    except NumberParseException:
        if not number.startswith("+") and not region:
            return {"ok": False, "error": "Add the country code (e.g. +33 6 12 34 56 78) or pick a region."}
        return {"ok": False, "error": "Couldn't parse that number."}

    valid = phonenumbers.is_valid_number(parsed)
    possible = phonenumbers.is_possible_number(parsed)
    region_code = phonenumbers.region_code_for_number(parsed)
    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    nat = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)

    return {
        "ok": True,
        "valid": valid,
        "possible": possible,
        "e164": e164,
        "international": intl,
        "national": nat,
        "country_code": parsed.country_code,
        "region": region_code,
        "location": geocoder.description_for_number(parsed, "en") or None,
        "carrier": carrier.name_for_number(parsed, "en") or None,
        "line_type": _TYPES.get(phonenumbers.number_type(parsed), "Unknown"),
        "timezones": list(timezone.time_zones_for_number(parsed)),
    }
