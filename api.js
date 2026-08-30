// api.js — every backend call goes through here. Nothing else in the
// frontend talks to fetch() directly, so the auth-token handling and
// base URL only need to be right in one place.

const TOKEN_KEY = "personal_ai_token";

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
}

async function apiFetch(path, options = {}) {
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

    if (res.status === 401) {
        setToken(null);
        window.location.href = "login.html";
        throw new Error("Unauthorized");
    }
    return res;
}

const api = {
    async session() {
        const res = await apiFetch("/api/session");
        return res.json();
    },
    async login(password) {
        const res = await apiFetch("/api/login", {
            method: "POST",
            body: JSON.stringify({ password }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Login failed");
        setToken(data.token);
        return data;
    },
    logout() {
        setToken(null);
        window.location.href = "login.html";
    },
    async sendMessage(text) {
        const res = await apiFetch("/api/message", {
            method: "POST",
            body: JSON.stringify({ text }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Request failed");
        return data;
    },
    async history() {
        const res = await apiFetch("/api/history");
        const data = await res.json();
        return data.history || [];
    },
    async projects() {
        const res = await apiFetch("/api/projects");
        const data = await res.json();
        return data.projects || [];
    },
    downloadUrl(project, filename) {
        const token = getToken();
        const suffix = token ? `?token=${encodeURIComponent(token)}` : "";
        return `${API_BASE_URL}/api/download/${encodeURIComponent(project)}/${encodeURIComponent(filename)}${suffix}`;
    },
};
