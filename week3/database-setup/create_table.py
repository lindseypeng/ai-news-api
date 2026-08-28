from database.session import Base, engine
from database.event import Event  # noqa: F401

def create_tables():
    """Create all tables defined in the models."""
    # Print all tables that will be created
    print("Tables to be created:")
    for table in Base.metadata.tables:
        print(f"- {table}")

    # Create the tables
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()
    print("Tables created successfully!")
