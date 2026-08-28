import uuid
from datetime import datetime

from database.event import Event
from database.repository import GenericRepository
from database.session import db_session


def store_event(event_repo: GenericRepository[Event]) -> Event:
    """Store a new event in the database."""
    # Create a new event
    new_event = Event(
        id=uuid.uuid4(),  # Generate a new UUID
        workflow_type="TestWorkflow",
        data={"message": "Hello, World!"},
        task_context={"status": "pending"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Store the event in the database
    stored_event = event_repo.create(new_event)
    print(f"Created event with ID: {stored_event.id}")
    return stored_event


def retrieve_event(event_repo: GenericRepository[Event], event_id: str) -> Event:
    """Retrieve an event from the database by ID."""
    retrieved_event = event_repo.get(event_id)
    return retrieved_event


def main():
    # Create a database session
    session = next(db_session())

    # Create a repository for Event model
    event_repo = GenericRepository(session, Event)

    # Store a new event
    stored_event = store_event(event_repo)

    # Retrieve the event we just created
    retrieved_event = retrieve_event(event_repo, str(stored_event.id))
    if retrieved_event:
        print("\nRetrieved event:")
        print(f"ID: {retrieved_event.id}")
        print(f"Workflow Type: {retrieved_event.workflow_type}")
        print(f"Data: {retrieved_event.data}")
        print(f"Task Context: {retrieved_event.task_context}")
        print(f"Created At: {retrieved_event.created_at}")
        print(f"Updated At: {retrieved_event.updated_at}")
    else:
        print(f"\nNo event found with ID: {stored_event.id}")


if __name__ == "__main__":
    main()
