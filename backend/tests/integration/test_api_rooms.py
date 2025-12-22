"""
Integration tests for room API endpoints.

Tests CRUD operations for rooms through the REST API.
"""

import pytest


class TestRoomEndpoints:
    """Tests for room API endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    async def test_create_room(self, authenticated_client):
        """Test creating a room via API."""
        client, token = authenticated_client

        response = await client.post("/rooms", json={"name": "test_room", "max_interactions": 10})

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_room"
        assert data["max_interactions"] == 10
        assert "id" in data

    @pytest.mark.integration
    @pytest.mark.api
    async def test_create_room_duplicate_name(self, authenticated_client):
        """Test creating a room with duplicate name."""
        client, token = authenticated_client

        # Create first room
        await client.post("/rooms", json={"name": "duplicate_room"})

        # Try to create second room with same name
        response = await client.post("/rooms", json={"name": "duplicate_room"})

        # The API returns 409 Conflict for duplicate names
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    @pytest.mark.integration
    @pytest.mark.api
    async def test_list_rooms(self, authenticated_client):
        """Test listing all rooms."""
        client, token = authenticated_client

        # Create multiple rooms
        await client.post("/rooms", json={"name": "room1"})
        await client.post("/rooms", json={"name": "room2"})
        await client.post("/rooms", json={"name": "room3"})

        # List rooms
        response = await client.get("/rooms")

        assert response.status_code == 200
        rooms = response.json()
        assert len(rooms) == 3
        assert {r["name"] for r in rooms} == {"room1", "room2", "room3"}

    @pytest.mark.integration
    @pytest.mark.api
    async def test_get_room(self, authenticated_client, sample_room):
        """Test getting a specific room."""
        client, token = authenticated_client

        response = await client.get(f"/rooms/{sample_room.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_room.id
        assert data["name"] == sample_room.name

    @pytest.mark.integration
    @pytest.mark.api
    async def test_get_room_not_found(self, authenticated_client):
        """Test getting a non-existent room."""
        client, token = authenticated_client

        response = await client.get("/rooms/999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.integration
    @pytest.mark.api
    async def test_update_room(self, authenticated_client, sample_room):
        """Test updating a room."""
        client, token = authenticated_client

        response = await client.patch(f"/rooms/{sample_room.id}", json={"max_interactions": 20, "is_paused": True})

        assert response.status_code == 200
        data = response.json()
        assert data["max_interactions"] == 20
        assert data["is_paused"] is True

    @pytest.mark.integration
    @pytest.mark.api
    async def test_delete_room(self, authenticated_client, sample_room):
        """Test deleting a room."""
        client, token = authenticated_client

        response = await client.delete(f"/rooms/{sample_room.id}")

        assert response.status_code == 200
        assert response.json()["message"] == "Room deleted successfully"

        # Verify room is deleted
        response = await client.get(f"/rooms/{sample_room.id}")
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.api
    async def test_delete_room_not_found(self, authenticated_client):
        """Test deleting a non-existent room."""
        client, token = authenticated_client

        response = await client.delete("/rooms/999")

        assert response.status_code == 404


class TestRoomAgentEndpoints:
    """Tests for room-agent relationship endpoints."""

    @pytest.mark.integration
    @pytest.mark.api
    async def test_add_agent_to_room(self, authenticated_client, sample_room, sample_agent):
        """Test adding an agent to a room."""
        client, token = authenticated_client

        response = await client.post(f"/rooms/{sample_room.id}/agents/{sample_agent.id}")

        assert response.status_code == 200
        # Returns the updated room, not a message
        room = response.json()
        assert room["id"] == sample_room.id

        # Verify agent was added
        response = await client.get(f"/rooms/{sample_room.id}/agents")
        agents = response.json()
        assert len(agents) == 1
        assert agents[0]["id"] == sample_agent.id

    @pytest.mark.integration
    @pytest.mark.api
    async def test_remove_agent_from_room(self, authenticated_client, sample_room_with_agents, sample_agent):
        """Test removing an agent from a room."""
        client, token = authenticated_client

        response = await client.delete(f"/rooms/{sample_room_with_agents.id}/agents/{sample_agent.id}")

        assert response.status_code == 200
        assert response.json()["message"] == "Agent removed from room successfully"

        # Verify agent was removed
        response = await client.get(f"/rooms/{sample_room_with_agents.id}/agents")
        agents = response.json()
        assert len(agents) == 0

    @pytest.mark.integration
    @pytest.mark.api
    async def test_get_agents_in_room(self, authenticated_client, sample_room):
        """Test getting agents in a room."""
        client, token = authenticated_client

        response = await client.get(f"/rooms/{sample_room.id}/agents")

        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, list)

    @pytest.mark.integration
    @pytest.mark.api
    async def test_add_nonexistent_agent_to_room(self, authenticated_client, sample_room):
        """Test adding a non-existent agent to a room."""
        client, token = authenticated_client

        response = await client.post(f"/rooms/{sample_room.id}/agents/999")

        assert response.status_code == 404
