from flask_babel import get_locale, numbers, dates

def format_currency_custom(amount, currency_code):
    if amount is None:
        amount = 0.0
    else:
        amount = float(amount)

    if not currency_code:
        return numbers.format_decimal(amount, locale=get_locale())

    try:
        return numbers.format_currency(amount, currency_code, locale=get_locale())
    except Exception:
        return f"{amount:,.2f} {currency_code}"

def format_date_custom(value, format='medium'):
    if value is None:
        return ""
    try:
        return dates.format_date(value, format=format, locale=get_locale())
    except Exception:
        return value.strftime('%Y-%m-%d')