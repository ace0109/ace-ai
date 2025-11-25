
def test_chat_session_management(client, user_headers):
    # 1. Create a session implicitly via chat
    chat_resp = client.post("/api/chat", json={"message": "Hello Session"}, headers=user_headers)
    assert chat_resp.status_code == 200
    # The response is a stream, we need to read it to trigger side effects (saving message)
    # and get the session_id
    lines = [
        line.decode() if isinstance(line, bytes) else line
        for line in chat_resp.iter_lines()
        if line
    ]
    
    # Parse session_id from the first chunk
    import json
    first_chunk = json.loads(lines[0].replace("data: ", ""))
    assert "session_id" in first_chunk
    session_id = first_chunk["session_id"]
    
    # 2. List sessions
    list_resp = client.get("/api/chat/sessions", headers=user_headers)
    assert list_resp.status_code == 200
    sessions = list_resp.json()["data"]
    assert len(sessions) > 0
    assert sessions[0]["id"] == session_id
    
    # 3. Get messages
    msgs_resp = client.get(f"/api/chat/sessions/{session_id}/messages", headers=user_headers)
    assert msgs_resp.status_code == 200
    messages = msgs_resp.json()["data"]
    # Should have user message and assistant message
    # Note: Assistant message is saved AFTER streaming. 
    # Since we consumed the stream in `lines = ...`, the background task/post-yield code should have run.
    # However, `chat_store.add_message` is called after the loop.
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello Session"
    assert messages[1]["role"] == "assistant"
    
    # 4. Chat with existing session
    chat_resp_2 = client.post("/api/chat", json={"message": "Follow up", "session_id": session_id}, headers=user_headers)
    assert chat_resp_2.status_code == 200
    # Consume stream
    list(chat_resp_2.iter_lines())
    
    msgs_resp_2 = client.get(f"/api/chat/sessions/{session_id}/messages", headers=user_headers)
    messages_2 = msgs_resp_2.json()["data"]
    assert len(messages_2) >= 4 # 2 previous + 2 new
    
    # 5. Delete session
    del_resp = client.delete(f"/api/chat/sessions/{session_id}", headers=user_headers)
    assert del_resp.status_code == 200
    
    # 6. Verify deletion
    list_resp_after = client.get("/api/chat/sessions", headers=user_headers)
    sessions_after = list_resp_after.json()["data"]
    assert not any(s["id"] == session_id for s in sessions_after)
