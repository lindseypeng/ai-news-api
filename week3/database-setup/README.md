# Database Setup for AI Application

This directory contains the Docker configuration for our AI application's infrastructure. Currently, it sets up with just a PostgreSQL database for storing events and results. Make sure Docker is installed and running.

## Project Structure

The project is organized as follows:

- `docker/`: Contains Docker configuration files
- `database/`: Reusable database components
  - `event.py`: Event model definition
  - `repository.py`: Generic repository pattern implementation
  - `session.py`: Database session management
  - `database_utils.py`: Utility functions for database operations
- `create_table.py`: Script to create database tables
- `connect.py`: Example script demonstrating database operations

## Database Components

The `database` folder contains reusable components that follow best practices:

- **Event Model**: Defines the structure for storing events with metadata
- **Repository Pattern**: Generic implementation for database operations
- **Session Management**: Handles database connections and sessions
- **Database Utils**: Common utility functions for database operations

## Docker Compose Configuration

Here's our `docker-compose.yml` explained:

```yaml
services:
  db:  # Service name
    image: postgres:16  # Using PostgreSQL version 16
    ports:
      - "5432:5432"  # Map container port to host port
    environment:
      - POSTGRES_USER=postgres      # Database user
      - POSTGRES_PASSWORD=postgres  # Database password
      - POSTGRES_DB=postgres        # Database name
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist data

volumes:
  postgres_data:  # Named volume for data persistence
```

## Usage Instructions

1. **Start the Database**:
   ```bash
   cd week-3/database-setup/docker
   docker compose up -d
   ```
   The `-d` flag runs in detached mode (background)

2. **Create Database Tables**:
   ```bash
   python create_table.py
   ```
   This will create the necessary tables in the database.

3. **Test Database Connection**:
   ```bash
   python connect.py
   ```
   This script demonstrates:
   - Creating a new event
   - Storing it in the database
   - Retrieving the event
   - Displaying the event details

4. **Stop the Database**:
   ```bash
   docker compose down
   ```
   Note: Data persists even after stopping

5. **Remove Everything** (including data):
   ```bash
   docker compose down -v
   ```
   The `-v` flag removes volumes

## Connecting to the Database

- **Host**: localhost
- **Port**: 5432
- **User**: postgres
- **Password**: postgres
- **Database**: postgres

Connection URL format: `postgresql://postgres:postgres@localhost:5432/postgres`

### Using GUI Tools to connect to your database
You can connect using your preferred database GUI:

- **DBeaver** (Free, all platforms): https://dbeaver.io/
- **pgAdmin** (Free, PostgreSQL specific): https://www.pgadmin.org/
- **DataGrip** (JetBrains paid, all platforms): https://www.jetbrains.com/datagrip/
- **TablePlus** (Freemium, macOS/Windows): https://tableplus.com/

## Data Persistence Explained

- Docker containers are ephemeral (temporary)
- Named volumes (`postgres_data`) persist data
- Data stored in volume survives:
  - Container restarts
  - Container removal
  - Docker Compose down
- Only removed when explicitly using `docker compose down -v`

## Common Issues

1. **Port Conflict**:
   - Error: "port 5432 already in use"
   - Solution: Stop other PostgreSQL instances or change port mapping

2. **Permission Issues**:
   - Error: "permission denied"
   - Solution: Use `sudo` or add user to docker group

3. **Connection Refused**:
   - Wait a few seconds after starting
   - Database needs time to initialize

## Next Steps

For more details on Docker and PostgreSQL, refer to:

- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Docker Hub](https://hub.docker.com/_/postgres)