# Tourismus

Tourismus is a test web application built with **Flask**, **HTMX**, and **Poetry**.

It is a lightweight project for experimenting with server-rendered pages and partial UI updates.

## Features

- Flask backend.
- HTMX-powered interactions.
- Poetry for dependency management.
- Simple structure for testing and development.

## Requirements

- Python 3.10 or newer.
- Poetry.
- Flask.
- HTMX.

## Installation

```bash
git clone https://github.com/Proxima5559/Tourismus.git
cd Tourismus
poetry install
```

If you use the Flask HTMX extension, add it with Poetry:

```bash
poetry add flask-htmx
```

## Run locally

```bash
poetry run flask run
```

If your app is exposed as a module, you can also use:

```bash
poetry run python -m flask run
```
