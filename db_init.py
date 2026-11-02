import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "shop.db"
JSON_PATH = Path(__file__).parent / "catalog.json"

def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS categories;

        CREATE TABLE categories (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE products (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            price        REAL NOT NULL CHECK (price >= 0),
            category_id  INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
                ON DELETE RESTRICT
                ON UPDATE CASCADE
        );

        CREATE INDEX idx_products_category ON products(category_id);
    """)

def load_catalog() -> list[dict]:
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)

def normalize(catalog: list[dict]) -> tuple[dict, list[dict]]:
    categories: dict[str, str] = {}
    products: list[dict] = []

    for item in catalog:
        cat = item["category"]
        categories[cat["name"]] = cat["description"]

        products.append({
            "product_name": item["product_name"],
            "price": item["price"],
            "category_name": cat["name"],
        })

    return categories, products

def insert_data(conn, categories, products):
    conn.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        list(categories.items()),
    )

    name_to_id = dict(conn.execute("SELECT name, id FROM categories"))

    conn.executemany(
        "INSERT INTO products (product_name, price, category_id) VALUES (?, ?, ?)",
        [(p["product_name"], p["price"], name_to_id[p["category_name"]])
         for p in products],
    )
    conn.commit()

def main():
    catalog = load_catalog()
    categories, products = normalize(catalog)

    with sqlite3.connect(DB_PATH) as conn:
        create_tables(conn)
        insert_data(conn, categories, products)

        print(f"Категорий: {len(categories)}")
        print(f"Товаров:   {len(products)}")

        try:
            conn.execute(
                "INSERT INTO products (product_name, price, category_id) VALUES (?, ?, ?)",
                ("Bad", 100, 9999),
            )
            print("FK не работает!")
        except sqlite3.IntegrityError:
            print("Внешний ключ работает: товар с несуществующей категорией отклонён")

if __name__ == "__main__":
    main()