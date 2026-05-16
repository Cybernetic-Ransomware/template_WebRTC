# WebRTC Template — task runner
# Install: scoop install just  |  winget install Casey.Just

set shell := ["powershell", "-Command"]

# Start full Docker stack (signaling + coturn + caddy) with rebuild
up:
    docker-compose -f docker/docker-compose.yml up --build -d

# Stop and remove Docker stack
down:
    docker-compose -f docker/docker-compose.yml down

# Show status of all containers
ps:
    docker-compose -f docker/docker-compose.yml ps

# Stream signaling server logs
logs:
    docker-compose -f docker/docker-compose.yml logs -f signaling

# Run the full linting suite
lint:
    uv run ruff format .
    uv run ruff check --fix .
    uv run ty check
    uv run codespell

# Run security scanner
security:
    uv run bandit -r backend/

# Start signaling server locally (without Docker)
run:
    uv run python -m webrtc_template

# Run tests
test:
    uv run pytest

# Run pre-commit hooks on staged files
check:
    uv run pre-commit run

# Start Vite frontend dev server
dev-frontend:
    npm --prefix frontend run dev

# Build frontend for production
build-frontend:
    npm --prefix frontend run build
