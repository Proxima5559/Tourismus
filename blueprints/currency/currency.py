from flask import Blueprint, render_template, request
import os
from decimal import Decimal
from dotenv import load_dotenv
from flask_login import login_required
from utils.extensions import http_session
from utils.decorators import confirmed_required

load_dotenv(".env")

currency_bp = Blueprint(
    "currency",
    __name__,
    template_folder="../../templates/currency"
)

EXCHANGE_RATE_API_KEY = os.getenv("EXCHANGE_RATE_API_KEY")

SUPPORTED_CURRENCIES = {
    "USD": "US Dollar",
    "EUR": "Euro",
    "RUB": "Russian Ruble",
    "GEL": "Georgian Lari",
    "IRR": "Iranian Rial",
    "AMD": "Armenian Dram",
    "CNY": "Chinese Yuan"
}

def convert_currency(amount, from_currency, to_currency):
    if not EXCHANGE_RATE_API_KEY:
        raise RuntimeError("ExchangeRate API key is missing")

    url = (
        f"https://v6.exchangerate-api.com/v6/"
        f"{EXCHANGE_RATE_API_KEY}/pair/{from_currency}/{to_currency}"
    )

    response = http_session.get(url, timeout=5)
    data = response.json()

    if data.get("result") != "success":
        raise ValueError(data)

    rate = Decimal(str(data["conversion_rate"])) 
    return (amount * rate).quantize(Decimal("0.01"))


@currency_bp.route("/exchange", methods=["GET", "POST"])
@login_required
@confirmed_required
def exchange():
    result = None
    error = None

    if request.method == "POST":
        try:
            amount = Decimal(request.form.get("amount", 0))
            from_currency = request.form.get("from_currency")
            to_currency = request.form.get("to_currency")

            if amount <= 0:
                raise ValueError("Invalid amount")

            converted = convert_currency(amount, from_currency, to_currency)
            result = f"{amount} {from_currency} = {converted:.2f} {to_currency}"

        except Exception as e:
            print("EXCHANGE ERROR:", repr(e))
            error = f"Could not fetch exchange rate for {from_currency} → {to_currency}."

    if request.method == "POST" and request.headers.get("HX-Request"):
        return render_template(
            "exchange_result.html",
            result=result,
            error=error
        )

    return render_template(
        "exchange.html",
        currencies=SUPPORTED_CURRENCIES,
        result=result,
        error=error
    )