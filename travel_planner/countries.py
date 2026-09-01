"""
countries.py — offline country reference data.

REST Countries v1-v4 were retired in 2026 and v5 requires an authenticated API
key, so relying on it would break this project's "works with zero keys" promise.
The small amount of data we actually need — currency code, primary language and
driving side — is stable enough to ship offline, keyed by the ISO 3166-1 alpha-2
code that Open-Meteo geocoding already returns.

Live exchange *rates* still come from the network; only the static mapping lives
here.
"""

from __future__ import annotations

#: ISO 3166-1 alpha-2 → ISO 4217 currency code.
COUNTRY_CURRENCY: dict[str, str] = {
    "AD": "EUR", "AE": "AED", "AF": "AFN", "AG": "XCD", "AL": "ALL", "AM": "AMD",
    "AO": "AOA", "AR": "ARS", "AT": "EUR", "AU": "AUD", "AZ": "AZN", "BA": "BAM",
    "BB": "BBD", "BD": "BDT", "BE": "EUR", "BF": "XOF", "BG": "BGN", "BH": "BHD",
    "BI": "BIF", "BJ": "XOF", "BN": "BND", "BO": "BOB", "BR": "BRL", "BS": "BSD",
    "BT": "BTN", "BW": "BWP", "BY": "BYN", "BZ": "BZD", "CA": "CAD", "CD": "CDF",
    "CF": "XAF", "CG": "XAF", "CH": "CHF", "CI": "XOF", "CL": "CLP", "CM": "XAF",
    "CN": "CNY", "CO": "COP", "CR": "CRC", "CU": "CUP", "CV": "CVE", "CY": "EUR",
    "CZ": "CZK", "DE": "EUR", "DJ": "DJF", "DK": "DKK", "DO": "DOP", "DZ": "DZD",
    "EC": "USD", "EE": "EUR", "EG": "EGP", "ER": "ERN", "ES": "EUR", "ET": "ETB",
    "FI": "EUR", "FJ": "FJD", "FR": "EUR", "GA": "XAF", "GB": "GBP", "GD": "XCD",
    "GE": "GEL", "GH": "GHS", "GM": "GMD", "GN": "GNF", "GQ": "XAF", "GR": "EUR",
    "GT": "GTQ", "GW": "XOF", "GY": "GYD", "HK": "HKD", "HN": "HNL", "HR": "EUR",
    "HT": "HTG", "HU": "HUF", "ID": "IDR", "IE": "EUR", "IL": "ILS", "IN": "INR",
    "IQ": "IQD", "IR": "IRR", "IS": "ISK", "IT": "EUR", "JM": "JMD", "JO": "JOD",
    "JP": "JPY", "KE": "KES", "KG": "KGS", "KH": "KHR", "KM": "KMF", "KR": "KRW",
    "KW": "KWD", "KZ": "KZT", "LA": "LAK", "LB": "LBP", "LI": "CHF", "LK": "LKR",
    "LR": "LRD", "LS": "LSL", "LT": "EUR", "LU": "EUR", "LV": "EUR", "LY": "LYD",
    "MA": "MAD", "MC": "EUR", "MD": "MDL", "ME": "EUR", "MG": "MGA", "MK": "MKD",
    "ML": "XOF", "MM": "MMK", "MN": "MNT", "MO": "MOP", "MR": "MRU", "MT": "EUR",
    "MU": "MUR", "MV": "MVR", "MW": "MWK", "MX": "MXN", "MY": "MYR", "MZ": "MZN",
    "NA": "NAD", "NE": "XOF", "NG": "NGN", "NI": "NIO", "NL": "EUR", "NO": "NOK",
    "NP": "NPR", "NZ": "NZD", "OM": "OMR", "PA": "PAB", "PE": "PEN", "PG": "PGK",
    "PH": "PHP", "PK": "PKR", "PL": "PLN", "PT": "EUR", "PY": "PYG", "QA": "QAR",
    "RO": "RON", "RS": "RSD", "RU": "RUB", "RW": "RWF", "SA": "SAR", "SC": "SCR",
    "SD": "SDG", "SE": "SEK", "SG": "SGD", "SI": "EUR", "SK": "EUR", "SL": "SLE",
    "SN": "XOF", "SO": "SOS", "SR": "SRD", "SS": "SSP", "SV": "USD", "SY": "SYP",
    "SZ": "SZL", "TD": "XAF", "TG": "XOF", "TH": "THB", "TJ": "TJS", "TM": "TMT",
    "TN": "TND", "TO": "TOP", "TR": "TRY", "TT": "TTD", "TW": "TWD", "TZ": "TZS",
    "UA": "UAH", "UG": "UGX", "US": "USD", "UY": "UYU", "UZ": "UZS", "VE": "VES",
    "VN": "VND", "VU": "VUV", "WS": "WST", "YE": "YER", "ZA": "ZAR", "ZM": "ZMW",
    "ZW": "ZWG",
}

#: ISO 4217 → (display name, symbol).
CURRENCY_INFO: dict[str, tuple[str, str]] = {
    "AED": ("UAE dirham", "د.إ"), "ARS": ("Argentine peso", "$"),
    "AUD": ("Australian dollar", "$"), "BAM": ("Bosnian mark", "KM"),
    "BGN": ("Bulgarian lev", "лв"), "BRL": ("Brazilian real", "R$"),
    "CAD": ("Canadian dollar", "$"), "CHF": ("Swiss franc", "Fr"),
    "CLP": ("Chilean peso", "$"), "CNY": ("Chinese yuan", "¥"),
    "COP": ("Colombian peso", "$"), "CZK": ("Czech koruna", "Kč"),
    "DKK": ("Danish krone", "kr"), "EGP": ("Egyptian pound", "£"),
    "EUR": ("Euro", "€"), "GBP": ("Pound sterling", "£"),
    "HKD": ("Hong Kong dollar", "$"), "HUF": ("Hungarian forint", "Ft"),
    "IDR": ("Indonesian rupiah", "Rp"), "ILS": ("Israeli new shekel", "₪"),
    "INR": ("Indian rupee", "₹"), "ISK": ("Icelandic króna", "kr"),
    "JPY": ("Japanese yen", "¥"), "KES": ("Kenyan shilling", "Sh"),
    "KRW": ("South Korean won", "₩"), "LKR": ("Sri Lankan rupee", "Rs"),
    "MAD": ("Moroccan dirham", "د.م."), "MXN": ("Mexican peso", "$"),
    "MYR": ("Malaysian ringgit", "RM"), "NOK": ("Norwegian krone", "kr"),
    "NZD": ("New Zealand dollar", "$"), "PEN": ("Peruvian sol", "S/"),
    "PHP": ("Philippine peso", "₱"), "PLN": ("Polish złoty", "zł"),
    "RON": ("Romanian leu", "lei"), "RSD": ("Serbian dinar", "дин"),
    "RUB": ("Russian ruble", "₽"), "SAR": ("Saudi riyal", "﷼"),
    "SEK": ("Swedish krona", "kr"), "SGD": ("Singapore dollar", "$"),
    "THB": ("Thai baht", "฿"), "TRY": ("Turkish lira", "₺"),
    "TWD": ("New Taiwan dollar", "NT$"), "USD": ("US dollar", "$"),
    "VND": ("Vietnamese dong", "₫"), "ZAR": ("South African rand", "R"),
}

#: Countries that drive on the left. Everywhere else drives on the right.
DRIVES_LEFT: frozenset[str] = frozenset(
    {
        "AG", "AU", "BB", "BD", "BN", "BS", "BW", "BT", "CY", "DM", "FJ", "GB",
        "GD", "GY", "HK", "ID", "IE", "IN", "JM", "JP", "KE", "KN", "LC", "LK",
        "LS", "MO", "MT", "MU", "MV", "MW", "MY", "MZ", "NA", "NP", "NZ", "PG",
        "PK", "SG", "SR", "SZ", "TH", "TL", "TO", "TT", "TZ", "UG", "VC", "WS",
        "ZA", "ZM", "ZW",
    }
)

#: Primary language for the most commonly searched travel destinations.
COUNTRY_LANGUAGE: dict[str, str] = {
    "AE": "Arabic", "AR": "Spanish", "AT": "German", "AU": "English",
    "BE": "Dutch", "BR": "Portuguese", "CA": "English", "CH": "German",
    "CL": "Spanish", "CN": "Mandarin Chinese", "CO": "Spanish", "CZ": "Czech",
    "DE": "German", "DK": "Danish", "EG": "Arabic", "ES": "Spanish",
    "FI": "Finnish", "FR": "French", "GB": "English", "GR": "Greek",
    "HR": "Croatian", "HU": "Hungarian", "ID": "Indonesian", "IE": "English",
    "IL": "Hebrew", "IN": "Hindi", "IS": "Icelandic", "IT": "Italian",
    "JP": "Japanese", "KE": "Swahili", "KR": "Korean", "LK": "Sinhala",
    "MA": "Arabic", "MX": "Spanish", "MY": "Malay", "NL": "Dutch",
    "NO": "Norwegian", "NP": "Nepali", "NZ": "English", "PE": "Spanish",
    "PH": "Filipino", "PL": "Polish", "PT": "Portuguese", "RO": "Romanian",
    "RS": "Serbian", "RU": "Russian", "SE": "Swedish", "SG": "English",
    "TH": "Thai", "TR": "Turkish", "TW": "Mandarin Chinese", "US": "English",
    "VN": "Vietnamese", "ZA": "English",
}


def lookup(country_code: str) -> dict[str, str] | None:
    """Return static facts for an ISO 3166-1 alpha-2 code, or ``None``."""
    code = (country_code or "").strip().upper()
    currency = COUNTRY_CURRENCY.get(code)
    if not currency:
        return None
    name, symbol = CURRENCY_INFO.get(currency, (currency, ""))
    return {
        "country_code": code,
        "currency_code": currency,
        "currency_name": name,
        "currency_symbol": symbol,
        "language": COUNTRY_LANGUAGE.get(code, ""),
        "drives_on": "left" if code in DRIVES_LEFT else "right",
        "source": "Built-in ISO 3166/4217 reference",
    }


__all__ = [
    "COUNTRY_CURRENCY",
    "COUNTRY_LANGUAGE",
    "CURRENCY_INFO",
    "DRIVES_LEFT",
    "lookup",
]
