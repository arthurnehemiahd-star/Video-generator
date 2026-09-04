/* api.js
All frontend communication with the backend goes through this file.
*/

const TOKEN_KEY = "video_generator_token";

function getToken() {
return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
if (token) {
localStorage.setItem(TOKEN_KEY, token);
} else {
localStorage.removeItem(TOKEN_KEY);
}
}

async function apiFetch(path, options = {}) {
const headers = {
"Content-Type": "application/json",
...(options.headers || {})
};

```
const token = getToken();

if (token) {
    headers["Authorization"] = `Bearer ${token}`;
}

const res = await fetch(
    `${API_BASE_URL}${path}`,
    {
        ...options,
        headers
    }
);

if (res.status === 401) {
    setToken(null);
    throw new Error("Unauthorized");
}

return res;
```

}

const api = {

```
async session() {
    const res = await apiFetch("/api/session");
    const data = await res.json();

    if (!res.ok) {
        throw new Error(
            data.error || "Could not check session"
        );
    }

    return data;
},

async login(password) {
    const res = await apiFetch(
        "/api/login",
        {
            method: "POST",
            body: JSON.stringify({
                password: password
            })
        }
    );

    const data = await res.json();

    if (!res.ok) {
        throw new Error(
            data.error || "Login failed"
        );
    }

    if (data.token) {
        setToken(data.token);
    }

    return data;
},

async sendMessage(text) {
    const res = await apiFetch(
        "/api/message",
        {
            method: "POST",
            body: JSON.stringify({
                text: text
            })
        }
    );

    const data = await res.json();

    if (!res.ok) {
        throw new Error(
            data.error || "Request failed"
        );
    }

    return data;
},

async history() {
    const res = await apiFetch("/api/history");
    const data = await res.json();

    if (!res.ok) {
        throw new Error(
            data.error || "Could not load history"
        );
    }

    return data.history || [];
},

async projects() {
    const res = await apiFetch("/api/projects");
    const data = await res.json();

    if (!res.ok) {
        throw new Error(
            data.error || "Could not load projects"
        );
    }

    return data.projects || [];
},

async generateVideo(description, duration) {
    const res = await apiFetch(
        "/api/generate-video",
        {
            method: "POST",
            body: JSON.stringify({
                description: description,
                duration: duration
            })
        }
    );

    const data = await res.json();

    if (!res.ok) {
        throw new Error(
            data.error || "Video generation failed"
        );
    }

    return data;
},

downloadUrl(project, filename) {
    const token = getToken();

    const suffix = token
        ? `?token=${encodeURIComponent(token)}`
        : "";

    return (
        `${API_BASE_URL}/api/download/` +
        `${encodeURIComponent(project)}/` +
        `${encodeURIComponent(filename)}` +
        suffix
    );
}
```

};

window.api = api;
