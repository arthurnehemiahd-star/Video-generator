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

const response = await fetch(
    `${API_BASE_URL}${path}`,
    {
        ...options,
        headers
    }
);

if (response.status === 401) {
    setToken(null);
}

return response;
```

}

const api = {

```
async session() {
    const response = await apiFetch("/api/session");
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Session check failed");
    }

    return data;
},

async login(password) {
    const response = await apiFetch("/api/login", {
        method: "POST",
        body: JSON.stringify({
            password: password
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Login failed");
    }

    if (data.token) {
        setToken(data.token);
    }

    return data;
},

async sendMessage(text) {
    const response = await apiFetch("/api/message", {
        method: "POST",
        body: JSON.stringify({
            text: text
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Message failed");
    }

    return data;
},

async history() {
    const response = await apiFetch("/api/history");
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Could not load history");
    }

    return data.history || [];
},

async projects() {
    const response = await apiFetch("/api/projects");
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Could not load projects");
    }

    return data.projects || [];
},

async generateVideo(description, duration) {
    const response = await apiFetch("/api/generate-video", {
        method: "POST",
        body: JSON.stringify({
            description: description,
            duration: duration
        })
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error || "Video generation failed"
        );
    }

    return data;
},

downloadUrl(project, filename) {
    const token = getToken();

    let url =
        `${API_BASE_URL}/api/download/` +
        `${encodeURIComponent(project)}/` +
        `${encodeURIComponent(filename)}`;

    if (token) {
        url += `?token=${encodeURIComponent(token)}`;
    }

    return url;
}
```

};

window.api = api;
