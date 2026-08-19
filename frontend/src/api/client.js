const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function getAuthHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

export async function sendQuery(query, chatSummary = null) {
  const res = await fetch(`${BASE_URL}/api/query`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders()
    },
    body: JSON.stringify({ query, chat_summary: chatSummary })
  });

  if (!res.ok) {
    if (res.status === 403) throw new Error("terms_required");
    if (res.status === 401) throw new Error("unauthorized");
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function getWeather(governorate) {
  const res = await fetch(`${BASE_URL}/api/weather/${encodeURIComponent(governorate)}`);
  if (!res.ok) throw new Error(`Weather API error: ${res.status}`);
  return res.json();
}

export async function getGovernorates() {
  const res = await fetch(`${BASE_URL}/api/governorates`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function sendQueryStream(query, chatSummary, onMetadata, onDone, onError) {
  try {
    const res = await fetch(`${BASE_URL}/api/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ query, chat_summary: chatSummary })
    });

    if (!res.ok) {
      if (res.status === 403) throw new Error("terms_required");
      if (res.status === 401) throw new Error("unauthorized");
      throw new Error(`API error: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6);
          if (!dataStr.trim()) continue;
          
          try {
            const data = JSON.parse(dataStr);
            if (data.type === 'metadata') {
              onMetadata(data);
            } else if (data.type === 'done') {
              onDone(data);
            }
          } catch (e) {
            console.error("Failed to parse SSE line", e);
          }
        }
      }
    }
  } catch (err) {
    onError(err);
  }
}
