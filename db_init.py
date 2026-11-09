import json
from pathlib import Path
from typing import List, Dict, Tuple

from sqlalchemy import create_engine, Column, Integer, Float, String, ForeignKey, CheckConstraint, event
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import IntegrityError

# --- 1. НАСТРОЙКА ПУТЕЙ ---
DB_PATH = Path(__file__).parent / "shop.db"
JSON_PATH = Path(__file__).parent / "catalog.json"

# --- 2. ОПИСАНИЕ МОДЕЛЕЙ (ТАБЛИЦ) ---
Base = declarative_base()


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category(name='{self.name}')>"


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete="RESTRICT"), nullable=False)

    category = relationship("Category", back_populates="products")

    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_positive'),
    )

    def __repr__(self):
        return f"<Product(name='{self.product_name}', price={self.price})>"


# --- 3. ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---

def load_catalog() -> List[dict]:
    with open(JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def normalize(catalog: List[dict]) -> Tuple[Dict[str, str], List[dict]]:
    categories: Dict[str, str] = {}
    products: List[dict] = []

    for item in catalog:
        cat = item["category"]
        categories[cat["name"]] = cat["description"]

        products.append({
            "product_name": item["product_name"],
            "price": item["price"],
            "category_name": cat["name"],
        })

    return categories, products


def main():
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Таблицы успешно созданы.")

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        catalog = load_catalog()
        categories_dict, products_list = normalize(catalog)

        db_categories = {}
        for name, desc in categories_dict.items():
            cat = Category(name=name, description=desc)
            session.add(cat)
            db_categories[name] = cat

        session.flush()

        for p in products_list:
            cat_obj = db_categories[p["category_name"]]
            prod = Product(
                product_name=p["product_name"],
                price=p["price"],
                category=cat_obj
            )
            session.add(prod)

        session.commit()
        print(f"Категорий добавлено: {len(db_categories)}")
        print(f"Товаров добавлено: {len(products_list)}")

        print("\nПроверяем ограничения...")
        try:
            bad_product = Product(product_name="Bad Product", price=100, category_id=9999)
            session.add(bad_product)
            session.commit()
            print("⚠️ Ошибка: Внешний ключ НЕ сработал!")
        except IntegrityError:
            session.rollback()
            print("✅ Успех: Внешний ключ работает (SQLAlchemy заблокировала вставку).")

    except Exception as e:
        session.rollback()
        print(f"Произошла ошибка: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
